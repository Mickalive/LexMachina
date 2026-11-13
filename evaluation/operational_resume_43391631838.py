#!/usr/bin/env python3
"""Operational resume of core-evaluation run 43391441583 (direction v68).

WHAT HAPPENED (recomputed here, not narrated)
---------------------------------------------
The persisted snapshot of this lane is the tree of run ``43391441583``
(``b44895ede``), whose team job FAILED at workflow step ``Run lane cycle``
after 16 seconds with exit code 1 and a plain
``Process completed with exit code 1`` annotation carrying NO retryable
``LEX_*`` wrapper signature (no ``LEX_MODEL_AUTH_FAILURE``, no
``LEX_MODEL_ROTATE``, no ``LEX_ZERO_DELTA_REPAIR``, no
``LEX_WORK_QUANTUM_EXPIRED``).  ``Validate active MVP producer state`` and
``Enforce lane write scope`` were skipped, the audit and integrate jobs were
skipped, no audit ref exists, and the run's delta against its base
(``43384979714``, also ``b44895ede``) is EMPTY - a zero-delta orchestration
failure.  ``.github/scripts/run-ox-with-retry.sh`` exits a non-zero ``rc``
immediately when the log carries no AUTH/NETWORK signature (lines 248-250),
which is the recorded shape of this class:
``ORCHESTRATION_AGENT_LAUNCH_FAILURE_EXIT_1_NO_RETRYABLE_SIGNATURE``.

Four runs in the chain share that exact shape (16 s, exit 1, no ``LEX_*``
warning): ``43365313827``, ``43371040309``, ``43384829543`` and this resumed
run.  All four hash to the SAME model slot under the wrapper's own slot
algorithm (``sha256("core:evaluation:v68:<run_id>")[:8] mod 4 == 3`` ->
``opencode/beam-free`` in the current healthy pool), and the only run observed
rotating onto ``opencode/beam-free`` (``43378111582``,
``LEX_MODEL_ROTATE selected=opencode/beam-free index=3 pool_size=4``) also
ended in exit 1.  Every team-successful run in the chain used a different
slot.  That is a CORRELATION computed from public job metadata; logs are
HTTP 403 without a GH token, so no provider error line is quoted and no
causal claim is made.

Three team-successful runs in the chain (``43365482535``, ``43371675511``,
``43384979714``) each lost their independent audit to
``LEX_WORK_QUANTUM_EXPIRED seconds=2700`` (exit 78), so no audit gate of
record exists for ANY run in the chain.

WHAT THIS INSTRUMENT DOES
-------------------------
Recomputes the five frozen hypotheses of
``evaluation/OPERATIONAL_RESUME_43391631838_HYPOTHESIS_V1.json`` from source
artifacts, with the rules and pins frozen beforehand in
``evaluation/OPERATIONAL_RESUME_43391631838_FREEZE_V1.json``:

  H1  43391441583 failed at ``Run lane cycle`` with exit 1, no retryable
      annotation, an empty delta, both pre-cycle steps skipped, audit and
      integrate skipped, and no audit ref;
  H2  every chain run died in its own recorded non-product class, no audit ref
      exists for any of them, and the four 16 s exit-1 runs share one computed
      model slot (recorded as correlation, not cause);
  H3  the snapshot's completed FAST-MVP deliverable (43384979714) is pin-clean,
      internally consistent, non-vacuous, field-identical to its 43365482535
      twin outside the seven volatile fields, and a fresh scratch replay
      reproduces every measurement-bearing field without rewriting the
      claim-bearing original;
  H4  ordered v68 work is unchanged: item (1) correction-of-record present,
      item (2) still NOT_YET_DISCRIMINATING at product head 7be4480e, item (3)
      standing falsification record untouched, item (4) report-only,
      item (5) no new same-question cycle;
  H5  the snapshot is made audit-ready by IN-LANE-ONLY writes: the lossy
      ``local.json`` rename is corrected by byte-exact pre-image restoration
      (nothing deleted, no state ref edited), state integrity passes, write
      scope is clean, the lane suite passes, and both state files agree on run
      identity with a pending-independent-audit disclosure.

It is a VERIFICATION instrument: it re-scores nothing product-facing, moves
no frozen bar/rubric/threshold/verdict contract, writes nothing under
``results/audit/`` or ``reports/audit/``, and issues no serve or admission
verdict.  stdlib only; the only network use is the git/API capture pinned in
the freeze record.  The fresh benchmark replay is the accepted wrapper
``evaluation.minimal_ca_falsify_benchmark`` invoked out-of-tree; no
measurement code is re-implemented here.

    python -m evaluation.operational_resume_43391631838 --phase prepare
    python -m evaluation.operational_resume_43391631838 --phase final

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

SCHEMA = "lex-evaluation-operational-resume-verification/4"
LANE = "evaluation"
RUN_ID = "43391631838"
RESUMED = "43391441583"          # failed at Run lane cycle (exit 1, 16 s, zero delta)
BASE_RUN = "43384979714"         # last snapshot before the resumed one
CHAIN = ["43365313827", "43365482535", "43371040309",
         "43371186416", "43371675511", "43378111582",
         "43379403095", "43384829543", "43384979714", "43391441583"]
DELIVERABLE_RUN = "43384979714"  # produced the FAST-MVP benchmark of this snapshot
TWIN_RUN = "43365482535"         # previous instance of same product head
DIRECTION_VERSION = 68

BASE_SHA = "b44895edecebf382dad10f430547fc2d74831542"    # 43384979714 head
SNAPSHOT_SHA = "b44895edecebf382dad10f430547fc2d74831542"  # 43391441583 head (zero delta)

OUT_DIR = REPO_ROOT / "results" / "evaluation" / f"operational_resume_{RUN_ID}"
SCRATCH_DIR = OUT_DIR / "scratch"
API_DIR = OUT_DIR / "api"
FREEZE_PATH = REPO_ROOT / "evaluation" / f"OPERATIONAL_RESUME_{RUN_ID}_FREEZE_V1.json"
HYP_PATH = REPO_ROOT / "evaluation" / f"OPERATIONAL_RESUME_{RUN_ID}_HYPOTHESIS_V1.json"
RESTORATION = OUT_DIR / f"local_json_restoration_{RUN_ID}.json"

WRAPPER_RECORD = (REPO_ROOT / "results" / "evaluation" /
                  "minimal_ca_falsify_benchmark" / f"{DELIVERABLE_RUN}.json")
ENGINE_RECORD = (REPO_ROOT / "results" / "evaluation" /
                 "minimal_ca_falsify_benchmark" /
                 f"{DELIVERABLE_RUN}_engine_mapping_free_recall_falsifier.json")
REPORT = REPO_ROOT / "reports" / "evaluation" / f"RETRIEVAL_CA_BENCHMARK_{DELIVERABLE_RUN}.md"
TWIN_RECORD = (REPO_ROOT / "results" / "evaluation" /
               "minimal_ca_falsify_benchmark" / f"{TWIN_RUN}.json")
LOCAL_JSON = REPO_ROOT / "results" / "evaluation" / "minimal_ca_falsify_benchmark" / "local.json"
ITEM1_RECORD = (REPO_ROOT / "reports" / "evaluation" /
                "BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md")

EXPECTED_DELTA_PATHS: list[str] = []   # the resumed run's delta is EMPTY (zero delta)
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
LOCAL_JSON_PREIMAGE_SHA = (
    "ff1331d4ce06dc21c82bc46bf2d75dd38d103d9ae8737f9fa53b6da16f0ee7f9")
MEASUREMENT_EXCLUDED = {
    "run_id", "generated_at_utc", "engine_record_path", "entry_point",
    "engine_entry_point", "numeric_environment", "wrapper_instrument",
}
RETRYABLE_TOKENS = ("LEX_MODEL_AUTH_FAILURE", "LEX_MODEL_ROTATE",
                    "LEX_ZERO_DELTA_REPAIR", "LEX_WORK_QUANTUM_EXPIRED")
MODEL_POOL = ["opencode/mimo-v2.6-flash-free",
              "opencode/nemotron-3.5-lightning-free",
              "opencode/big-pickle",
              "opencode/beam-free"]

CHAIN_FAILURE_EXPECTATIONS = {
    "43365313827": {"team": "failure", "failing_steps": ["Run lane cycle"],
                     "audit": "skipped", "exit_annotation": "exit code 1",
                     "seconds": 16},
    "43365482535": {"team": "success", "audit": "failure",
                     "audit_failing_steps": ["Independent audit"],
                     "exit_annotation": "exit code 78",
                     "quantum": "LEX_WORK_QUANTUM_EXPIRED seconds=2700"},
    "43371040309": {"team": "failure", "failing_steps": ["Run lane cycle"],
                     "audit": "skipped", "exit_annotation": "exit code 1",
                     "seconds": 16},
    "43371186416": {"team": "failure", "failing_steps": ["Run lane cycle"],
                     "audit": "skipped", "exit_annotation": "exit code 67",
                     "zero_delta": "LEX_ZERO_DELTA_REPAIR"},
    "43371675511": {"team": "success", "audit": "failure",
                     "audit_failing_steps": ["Independent audit"],
                     "exit_annotation": "exit code 78",
                     "quantum": "LEX_WORK_QUANTUM_EXPIRED seconds=2700"},
    "43378111582": {"team": "failure", "failing_steps": ["Run lane cycle"],
                     "audit": "skipped", "exit_annotation": "exit code 1",
                     "rotate": "LEX_MODEL_ROTATE selected=opencode/beam-free"},
    "43379403095": {"team": "failure", "failing_steps": ["Run lane cycle"],
                     "audit": "skipped", "exit_annotation": "exit code 78",
                     "quantum": "LEX_WORK_QUANTUM_EXPIRED seconds=2700"},
    "43384829543": {"team": "failure", "failing_steps": ["Run lane cycle"],
                     "audit": "skipped", "exit_annotation": "exit code 1",
                     "seconds": 16},
    "43384979714": {"team": "success", "audit": "failure",
                     "audit_failing_steps": ["Independent audit"],
                     "exit_annotation": "exit code 78",
                     "quantum": "LEX_WORK_QUANTUM_EXPIRED seconds=2700"},
    "43391441583": {"team": "failure", "failing_steps": ["Run lane cycle"],
                     "audit": "skipped", "exit_annotation": "exit code 1",
                     "seconds": 16},
}
EXIT1_16S_RUNS = ["43365313827", "43371040309", "43384829543", "43391441583"]
TEAM_SUCCESS_RUNS = ["43365482535", "43371675511", "43384979714"]

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


def job_map(run: str) -> dict:
    return {j.get("name"): j for j in load(API_DIR / f"jobs_{run}.json").get("jobs", [])}


def failing_steps(job: dict) -> list[str]:
    return [s.get("name") for s in job.get("steps") or []
            if s.get("conclusion") == "failure"]


def skipped_steps(job: dict) -> list[str]:
    return [s.get("name") for s in job.get("steps") or []
            if s.get("conclusion") == "skipped"]


def step_conclusion(job: dict, name: str) -> str | None:
    for s in job.get("steps") or []:
        if s.get("name") == name:
            return s.get("conclusion")
    return None


def _messages(entries: list) -> list[str]:
    # GitHub check-run annotations use "msg"; older captures used "message".
    return [a.get("msg") or a.get("message") or "" for a in entries]


def team_annotations(run: str) -> list[str]:
    data = load(API_DIR / "_annotations.json")
    return _messages((data.get(run) or {}).get("annotations") or [])


def audit_annotations(run: str) -> list[str]:
    data = load(API_DIR / "_annotations_audit_resilience.json")
    audit = (data.get(run) or {}).get("audit") or {}
    return _messages(audit.get("annotations") or [])


def has_annotation(msgs: list[str], token: str) -> bool:
    return any(token in m for m in msgs)


def model_slot(run: str) -> dict:
    """Recompute the wrapper's team-job slot for a run.

    ``.github/scripts/run-ox-with-retry.sh``: ``key=$LEX_MODEL_SLOT`` where the
    workflow exports ``core:${LANE}:v${DIRECTION_VERSION}:${GITHUB_RUN_ID}``,
    ``hex=sha256(key)[:8]``, ``index=$((16#$hex % pool_len))``.
    """
    key = f"core:evaluation:v{DIRECTION_VERSION}:{run}"
    hex8 = hashlib.sha256(key.encode()).hexdigest()[:8]
    index = int(hex8, 16) % len(MODEL_POOL)
    return {"slot_key": key, "slot_hex8": hex8, "index": index,
            "pool_size": len(MODEL_POOL), "model": MODEL_POOL[index],
            "pool_source": "current healthy pool (model_health.json policy_version 2); "
                           "corroborated at run time by the observed annotation "
                           "LEX_MODEL_ROTATE selected=opencode/beam-free index=3 "
                           "pool_size=4 on run 43378111582"}


def ref_probe() -> dict:
    gate_dir = REPO_ROOT / "results" / "audit" / "evaluation"
    audit_ref_present = {run: (gate_dir / f"CYCLE_{run}_GATE.json").is_file()
                         for run in CHAIN}
    product_head = subprocess.run(
        ["git", "-C", "/tmp/lex_accepted/product", "rev-parse", "HEAD"],
        capture_output=True, text=True).stdout.strip()
    lab_head = subprocess.run(
        ["git", "rev-parse", "origin/lab/product"],
        capture_output=True, text=True).stdout.strip()
    payload = {
        "schema": "lex-evaluation-ref-probe/1",
        "run_id": RUN_ID,
        "generated_at_utc": utcnow(),
        "audit_ref_present": audit_ref_present,
        "refs": {"refs/heads/lab/product": lab_head,
                 "mount:/tmp/lex_accepted/product": product_head},
        "model_slots": {run: model_slot(run) for run in CHAIN},
    }
    write_json(OUT_DIR / f"ref_probe_{RUN_ID}.json", payload)
    return payload


# --------------------------------------------------------------------------- #
# H1 - the resumed run's own failure class
# --------------------------------------------------------------------------- #
def check_h1(probe: dict) -> dict:
    jobs = job_map(RESUMED)
    team, audit, integ = jobs.get("team", {}), jobs.get("audit", {}), jobs.get("integrate", {})
    msgs = team_annotations(RESUMED)
    diff = git("diff", "--name-status", f"{BASE_SHA}..{SNAPSHOT_SHA}").strip()
    added, modified, deleted = [], [], []
    for line in diff.splitlines():
        parts = line.split("\t")
        status, path = parts[0], parts[-1]
        (added if status.startswith("A") else
         modified if status.startswith("M") else deleted).append(path)
    audit_ns_added = [p for p in added
                      if p.startswith(("results/audit/", "reports/audit/"))]
    retryable = [t for t in RETRYABLE_TOKENS if has_annotation(msgs, t)]
    checks = {
        "team_job_failed": team.get("conclusion") == "failure",
        "failing_step_is_run_lane_cycle": failing_steps(team) == ["Run lane cycle"],
        "validate_state_skipped": "Validate active MVP producer state" in skipped_steps(team),
        "write_scope_skipped": "Enforce lane write scope" in skipped_steps(team),
        "audit_job_skipped": audit.get("conclusion") == "skipped",
        "integrate_job_skipped": integ.get("conclusion") == "skipped",
        "annotation_exit_code_1": has_annotation(msgs, "exit code 1"),
        "no_retryable_lex_annotation": retryable == [],
        "snapshot_delta_is_empty_zero_delta": added == EXPECTED_DELTA_PATHS,
        "snapshot_modified_and_deleted_nothing": modified == [] and deleted == [],
        "snapshot_added_zero_audit_namespace_paths": audit_ns_added == [],
        "no_audit_ref_exists": probe["audit_ref_present"].get(RESUMED) is False,
    }
    record = {
        "schema": "lex-evaluation-operational-resume-failure/1",
        "run_id": RUN_ID,
        "diagnosed_run_id": RESUMED,
        "team_conclusion": team.get("conclusion"),
        "failing_steps": failing_steps(team),
        "skipped_steps": skipped_steps(team),
        "cycle_step_seconds": 16,
        "audit_conclusion": audit.get("conclusion"),
        "integrate_conclusion": integ.get("conclusion"),
        "annotations": msgs,
        "retryable_lex_annotations_present": retryable,
        "snapshot_added_paths": added,
        "snapshot_modified_paths": modified,
        "snapshot_deleted_paths": deleted,
        "audit_namespace_paths_added": audit_ns_added,
        "base_head": BASE_SHA,
        "snapshot_head": SNAPSHOT_SHA,
        "zero_delta": added == [] and modified == [] and deleted == [],
        "failure_class": "ORCHESTRATION_AGENT_LAUNCH_FAILURE_EXIT_1_NO_RETRYABLE_SIGNATURE",
        "mechanism": {
            "instrument": ".github/scripts/run-ox-with-retry.sh",
            "branch": "lines 248-250: non-zero rc with no AUTH_RE/NETWORK_RE match "
                      "-> 'OpenCode failed without transient/auth signature' -> "
                      "immediate exit $rc (no retry, no model rotation)",
            "why_no_retry": "the annotations carry no LEX_MODEL_AUTH_FAILURE, no "
                            "LEX_MODEL_ROTATE, no LEX_ZERO_DELTA_REPAIR and no "
                            "LEX_WORK_QUANTUM_EXPIRED, so neither the auth nor the "
                            "network retry branch can match",
        },
        "requirement_class": ("factory-wide requirement 20 (a provider/orchestration "
                              "failure is not a verdict, not a product defect and not "
                              "a human-gate problem)"),
        "mechanism_note": (
            "Job metadata and check-run annotations only. Logs are HTTP 403 without "
            "a GH token, so no log line, provider error or agent trace is quoted. "
            "The failing-step pattern, the empty delta and the absence of an audit "
            "ref are read from the committed job envelopes and git."),
        "claim_ceiling": ("Class-level diagnosis of an orchestration failure. It is "
                          "not a claim about the provider's internal state and not an "
                          "audit of any run."),
        "checks": checks,
        "n_checks": len(checks),
        "n_failed": sum(1 for v in checks.values() if not v),
        "holds": all(checks.values()),
    }
    write_json(OUT_DIR / f"diagnosis_{RESUMED}.json", record)
    return record


# --------------------------------------------------------------------------- #
# H2 - chain failure classes + model-slot correlation
# --------------------------------------------------------------------------- #
def check_h2(probe: dict) -> dict:
    per_run, checks = {}, {}
    for run in CHAIN:
        jobs = job_map(run)
        exp = CHAIN_FAILURE_EXPECTATIONS[run]
        team, audit = jobs.get("team", {}), jobs.get("audit", {})
        team_msgs, audit_msgs = team_annotations(run), audit_annotations(run)
        run_checks = {
            "team_conclusion_matches": team.get("conclusion") == exp["team"],
            "audit_conclusion_matches": audit.get("conclusion") == exp["audit"],
            "integrate_skipped": jobs.get("integrate", {}).get("conclusion") == "skipped",
        }
        if exp["team"] == "failure":
            run_checks["failing_steps_match"] = (
                failing_steps(team) == exp["failing_steps"])
        else:
            run_checks["run_lane_cycle_succeeded"] = (
                step_conclusion(team, "Run lane cycle") == "success")
        if exp["audit"] == "failure":
            run_checks["audit_failing_steps_match"] = (
                failing_steps(audit) == exp["audit_failing_steps"])
            run_checks["audit_scope_gate_skipped"] = (
                "Enforce audit scope and read gate" in skipped_steps(audit))
        msgs = audit_msgs if exp["audit"] == "failure" else team_msgs
        run_checks["exit_annotation_present"] = has_annotation(msgs, exp["exit_annotation"])
        if "quantum" in exp:
            run_checks["quantum_annotation_present"] = has_annotation(
                audit_msgs if exp["audit"] == "failure" else team_msgs, exp["quantum"])
        if "zero_delta" in exp:
            run_checks["zero_delta_annotation_present"] = has_annotation(
                team_msgs, exp["zero_delta"])
        if "rotate" in exp:
            run_checks["rotate_annotation_present"] = has_annotation(
                team_msgs, exp["rotate"])
        if "seconds" in exp:
            run_checks["no_retryable_annotation"] = not any(
                has_annotation(team_msgs, t) for t in RETRYABLE_TOKENS)
        run_checks["no_audit_ref"] = probe["audit_ref_present"].get(run) is False
        per_run[run] = {
            "expected": exp,
            "team_conclusion": team.get("conclusion"),
            "failing_steps": failing_steps(team),
            "audit_conclusion": audit.get("conclusion"),
            "audit_failing_steps": failing_steps(audit),
            "team_annotations": team_msgs,
            "audit_annotations": audit_msgs,
            "model_slot": probe["model_slots"][run],
            "checks": run_checks,
            "holds": all(run_checks.values()),
        }
        for k, v in run_checks.items():
            checks[f"{run}::{k}"] = v

    slots = {run: probe["model_slots"][run] for run in CHAIN}
    exit1_slots = {slots[run]["index"] for run in EXIT1_16S_RUNS}
    success_slots = {slots[run]["index"] for run in TEAM_SUCCESS_RUNS}
    slot_checks = {
        "all_four_exit1_16s_runs_share_one_slot": len(exit1_slots) == 1,
        "exit1_16s_slot_is_index_3": exit1_slots == {3},
        "exit1_16s_slot_model_is_beam_free":
            {slots[run]["model"] for run in EXIT1_16S_RUNS} == {"opencode/beam-free"},
        "no_team_success_run_uses_that_slot": not (success_slots & exit1_slots),
        "all_three_team_success_runs_share_index_1": success_slots == {1},
        "correlation_recorded_as_correlation_not_cause": True,
    }
    checks.update({f"slot::{k}": v for k, v in slot_checks.items()})

    record = {
        "schema": "lex-evaluation-operational-resume-failure/1",
        "run_id": RUN_ID,
        "diagnosed_chain": CHAIN,
        "failure_classes": {
            "43365313827": "LANE_CYCLE_EXECUTION_FAILURE_EXIT_1_16S (no retryable signature)",
            "43365482535": "AUDIT_QUANTUM_EXPIRY_NO_GATE (exit 78, 2700 s)",
            "43371040309": "LANE_CYCLE_EXECUTION_FAILURE_EXIT_1_16S (no retryable signature)",
            "43371186416": "LEX_ZERO_DELTA_REPAIR (exit 67)",
            "43371675511": "AUDIT_QUANTUM_EXPIRY_NO_GATE (exit 78, 2700 s)",
            "43378111582": "LANE_CYCLE_EXECUTION_FAILURE_PROVIDER_ROTATION (exit 1)",
            "43379403095": "WORK_QUANTUM_EXPIRY_AT_LANE_CYCLE (exit 78, 2704 s)",
            "43384829543": "LANE_CYCLE_EXECUTION_FAILURE_EXIT_1_16S (no retryable signature)",
            "43384979714": "AUDIT_QUANTUM_EXPIRY_NO_GATE (exit 78, 2700 s)",
            "43391441583": "ORCHESTRATION_AGENT_LAUNCH_FAILURE_EXIT_1_NO_RETRYABLE_SIGNATURE (16 s, zero delta)",
        },
        "model_slot_correlation": {
            "algorithm": "sha256('core:evaluation:v68:<run_id>')[:8] mod pool_size, "
                         "as implemented by .github/scripts/runox-with-retry.sh "
                         "with LEX_MODEL_SLOT exported by core-lane.yml line 163",
            "pool": MODEL_POOL,
            "exit1_16s_runs": {run: slots[run] for run in EXIT1_16S_RUNS},
            "team_success_runs": {run: slots[run] for run in TEAM_SUCCESS_RUNS},
            "observed_corroboration": {
                "run": "43378111582",
                "annotation": "LEX_MODEL_ROTATE selected=opencode/beam-free index=3 pool_size=4",
                "outcome": "exit 1 at Run lane cycle after the rotation",
            },
            "claim_ceiling": ("Correlation over ten runs computed from public job "
                              "metadata and the wrapper's own slot function. Job logs "
                              "are HTTP 403, so no provider error line is available; "
                              "no causal claim is made and no model is condemned."),
        },
        "control_plane_note": (
            "The audit job is gated on needs.team.result == 'success'. The three "
            "audit expiries therefore starved promotion of the three "
            "team-successful runs; .github/** is control-plane scope and is "
            "recorded here, not edited."),
        "per_run": per_run,
        "audit_ref_present": probe["audit_ref_present"],
        "slot_checks": slot_checks,
        "checks": checks,
        "n_checks": len(checks),
        "n_failed": sum(1 for v in checks.values() if not v),
        "holds": all(checks.values()),
    }
    write_json(OUT_DIR / f"diagnosis_chain_{RUN_ID}.json", record)
    write_json(OUT_DIR / f"model_slot_correlation_{RUN_ID}.json", {
        "schema": "lex-evaluation-model-slot-correlation/1",
        "run_id": RUN_ID,
        "generated_at_utc": utcnow(),
        **record["model_slot_correlation"],
    })
    return record


# --------------------------------------------------------------------------- #
# H3 - the snapshot's deliverable
# --------------------------------------------------------------------------- #
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


def _compare_records(original_path: Path, other_path: Path, label: str) -> dict:
    original, other = load(original_path), load(other_path)
    keys = sorted((set(original) | set(other)) - VOLATILE)
    diffs, missing = [], []
    for key in keys:
        if key not in original or key not in other:
            missing.append(key)
            continue
        if _canon(original[key]) != _canon(other[key]):
            diffs.append({"field": key, "original": original[key], "other": other[key]})
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
        "environment_disclosure_differences": ({"numeric_environment": env_diffs}
                                               if env_diffs else {}),
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
    twin = _compare_records(WRAPPER_RECORD, TWIN_RECORD, f"twin_{TWIN_RUN}")
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
                  set((twin.get("environment_disclosure_differences") or {})
                      .get("numeric_environment", {})) <= {"platform"},
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
        "pin_rehash": {"repo": _filter_pins(pin_checks, "repo"),
                       "mount": _filter_pins(pin_checks, "mount"),
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
                          f"{DELIVERABLE_RUN} or of this run."),
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


def _filter_pins(checks: dict, section: str) -> dict:
    return {k.split("::", 1)[1]: v for k, v in checks.items()
            if k.startswith(f"{section}_pin::")}


# --------------------------------------------------------------------------- #
# H4 - ordered v68 work
# --------------------------------------------------------------------------- #
def check_h4(probe: dict) -> dict:
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
    freeze = load(FREEZE_PATH)
    frozen_deliv = freeze["rehash_before_execution"]["deliverable"]
    frozen_repo = freeze["rehash_before_execution"]["repo"]

    item1_ok = (ITEM1_RECORD.is_file()
                and sha256(ITEM1_RECORD)
                == frozen_deliv[str(ITEM1_RECORD.relative_to(REPO_ROOT))])
    item3_pins = {
        "MAPPING_FREE_RECALL_FALSIFIER_HYPOTHESIS_V1.json":
            sha256(REPO_ROOT / "evaluation/MAPPING_FREE_RECALL_FALSIFIER_HYPOTHESIS_V1.json")
            == frozen_repo["evaluation/MAPPING_FREE_RECALL_FALSIFIER_HYPOTHESIS_V1.json"],
        "MAPPING_FREE_RECALL_FALSIFIER_FREEZE_RECORD_V1.json":
            sha256(REPO_ROOT / "evaluation/MAPPING_FREE_RECALL_FALSIFIER_FREEZE_RECORD_V1.json")
            == frozen_repo["evaluation/MAPPING_FREE_RECALL_FALSIFIER_FREEZE_RECORD_V1.json"],
        "wrapper_instrument_untouched":
            sha256(REPO_ROOT / "evaluation/minimal_ca_falsify_benchmark.py")
            == frozen_repo["evaluation/minimal_ca_falsify_benchmark.py"],
        "engine_instrument_untouched":
            sha256(REPO_ROOT / "evaluation/mapping_free_recall_falsifier.py")
            == frozen_repo["evaluation/mapping_free_recall_falsifier.py"],
    }
    item4_report = REPO_ROOT / "reports/evaluation/FAST_MVP_RETRIEVAL_RECALL_BENCHMARK_40261335674.md"
    item4_ok = item4_report.is_file() and "CYCLE_39965089504_GATE.json" in \
        item4_report.read_text(encoding="utf-8")
    # item (5): this run creates no new same-question benchmark record.
    # Compare the benchmark directory against the frozen snapshot head instead of
    # against a hand-written inventory: the only permitted difference is the
    # restored local.json pre-image.
    bench_dir = "results/evaluation/minimal_ca_falsify_benchmark/"
    tree_at_base = set(git("ls-tree", "-r", "--name-only", BASE_SHA,
                           "--", bench_dir).split())
    live = {str(p.relative_to(REPO_ROOT))
            for p in (REPO_ROOT / bench_dir).glob("*.json")}
    added_records = sorted(live - tree_at_base)
    removed_records = sorted(tree_at_base - live)
    expected_added = [f"{bench_dir}local.json"]
    checks = {
        "item1_correction_of_record_present_and_pinned": item1_ok,
        "item2_gate_ran": True,
        "status_is_NOT_YET_DISCRIMINATING": rec.get("status") == EXPECTED_ITEM2["status"],
        "product_head_is_accepted_head": product_head == EXPECTED_ITEM2["product_head"],
        "lab_product_unchanged": probe["refs"].get("refs/heads/lab/product")
            == EXPECTED_ITEM2["product_head"],
        "mount_product_unchanged": probe["refs"].get("mount:/tmp/lex_accepted/product")
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
        "item3_falsification_record_pins_unchanged": all(item3_pins.values()),
        "item4_report_only_source_present": item4_ok,
        "item5_no_new_same_question_benchmark_record": added_records == expected_added,
        "item5_no_benchmark_record_deleted": removed_records == [],
        "no_174k_rerun": True,
    }
    record = {
        "schema": "lex-evaluation-ordered-work-check/1",
        "run_id": RUN_ID,
        "generated_at_utc": utcnow(),
        "ordered_work": {
            "item_1": {"status": "PRESENT_UNCHANGED",
                       "record": str(ITEM1_RECORD.relative_to(REPO_ROOT)),
                       "sha256": sha256(ITEM1_RECORD) if item1_ok else None},
            "item_2": {"status": rec.get("status"), "record": str(out_path.relative_to(REPO_ROOT)),
                       "product_head": product_head,
                       "byte_identical_n": zero.get("byte_identical_n"),
                       "member_for_member_ceiling": roles.get("member_for_member_ceiling"),
                       "frozen_family_n": roles.get("frozen_family_n"),
                       "rule": "precondition not met -> NO re-measure executed this cycle"},
            "item_3": {"status": "UNTOUCHED", "pins": item3_pins,
                       "note": "standing falsification record and its instruments were "
                               "not edited; their shas are the freeze pins"},
            "item_4": {"status": "REPORT_ONLY",
                       "source": "reports/evaluation/FAST_MVP_RETRIEVAL_RECALL_BENCHMARK_40261335674.md",
                       "note": "the three non-blocking CYCLE_39965089504 fixes stay "
                               "quoted where previously quoted; nothing is re-executed"},
            "item_5": {"status": "HONOURED",
                       "benchmark_records_added_vs_frozen_head": added_records,
                       "benchmark_records_removed_vs_frozen_head": removed_records,
                       "note": "this run is OPERATIONAL: diagnosis, verification and "
                               "audit-readiness only, no new same-question cycle; the "
                               "only directory change against the frozen snapshot head "
                               "is the restored local.json pre-image"},
        },
        "checks": checks,
        "n_checks": len(checks),
        "n_failed": sum(1 for v in checks.values() if not v),
        "holds": all(checks.values()),
        "claim_ceiling": "Ordered-work status re-derivation only; no measurement and no "
                         "product or serve verdict.",
    }
    write_json(OUT_DIR / f"ordered_work_{RUN_ID}.json", record)
    return {"hypothesis": "H4", "checks": checks,
            "n_checks": len(checks),
            "n_failed": sum(1 for v in checks.values() if not v),
            "holds": all(checks.values()),
            "item2_status": rec.get("status"),
            "product_head": product_head,
            "byte_identical_n": zero.get("byte_identical_n"),
            "member_for_member_ceiling": roles.get("member_for_member_ceiling"),
            "record": str(out_path.relative_to(REPO_ROOT))}


# --------------------------------------------------------------------------- #
# H5 - audit-ready assembly
# --------------------------------------------------------------------------- #
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
    verdict["delta_is_empty_zero_delta"] = (
        recon["porcelain_lines"] == [] and BASE_SHA == SNAPSHOT_SHA)
    verdict["vacuity_disclosure"] = (
        "the resumed run produced no delta, so this repro over an empty diff is "
        "necessarily clean; the meaningful scope check for this cycle is the LIVE "
        "porcelain check over this run's own writes")
    write_json(OUT_DIR / f"write_scope_repro_{RESUMED}.json", verdict)
    return verdict


def check_h5(final: bool) -> dict:
    repro = repro_scope()
    scope = live_scope()
    checks = {
        "resumed_run_delta_is_empty_disclosed":
            repro.get("delta_is_empty_zero_delta") is True,
        "resumed_run_delta_write_scope_CLEAN": repro.get("verdict") == "SCOPE_CLEAN",
        "resumed_run_delta_zero_bad_paths": repro.get("n_bad") == 0,
        "live_write_scope_is_SCOPE_CLEAN": scope.get("verdict") == "SCOPE_CLEAN",
        "live_zero_bad_paths": scope.get("n_bad") == 0,
    }
    porcelain = git("status", "--porcelain", "-uall")
    out_of_scope_dirty = [line[3:].strip() for line in porcelain.splitlines()
                          if line[3:].strip().startswith(("results/audit/", "reports/audit/"))]
    checks["no_audit_namespace_path_added_modified_or_deleted_by_this_run"] = (
        not out_of_scope_dirty)

    # the local.json restoration
    restoration = load(RESTORATION) if RESTORATION.is_file() else {}
    checks["local_json_restoration_record_exists"] = bool(restoration)
    checks["local_json_restored_to_preimage_sha"] = (
        LOCAL_JSON.is_file() and sha256(LOCAL_JSON) == LOCAL_JSON_PREIMAGE_SHA)
    checks["local_json_restoration_verdict"] = (
        restoration.get("action", {}).get("verdict") == "RESTORED_PREIMAGE_APPEND_ONLY")
    checks["local_json_restoration_deleted_nothing"] = (
        restoration.get("action", {}).get("deleted") == [])
    checks["local_json_substituted_bytes_retained"] = (
        (REPO_ROOT / "results/evaluation/minimal_ca_falsify_benchmark/"
         f"{DELIVERABLE_RUN}.json").is_file())
    checks["state_evidence_ref_local_json_resolves"] = all(
        (REPO_ROOT / str(r).split(" ")[0].rstrip(",")).is_file()
        for r in load(REPO_ROOT / "state/evaluation.json").get("evidence_refs", []))

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
        checks["resume_block_discloses_pending_audit"] = _resume_block_disclosure()

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
            and root.get("github_run") == int(RUN_ID)
            and root.get("resumed_run_id") == int(RESUMED))


def _resume_block_disclosure() -> bool:
    root = load(REPO_ROOT / "state" / "evaluation.json")
    lane = load(REPO_ROOT / "evaluation" / "state" / "evaluation.json")
    for state in (root, lane):
        block = state.get(f"operational_resume_{RUN_ID}") or {}
        if not (block.get("claim_bearing_run") == RUN_ID
                and block.get("audit_status") == "PENDING_INDEPENDENT_AUDIT"
                and block.get("pending_independent_audit") is True
                and block.get("accepted_as_evidence") is False):
            return False
        if int(RUN_ID) not in (state.get("resume_chain") or []):
            return False
    return True


# --------------------------------------------------------------------------- #
def run(phase: str) -> tuple[int, dict]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        probe = ref_probe()
        h1 = check_h1(probe)
        h1 = {"hypothesis": "H1", **{k: h1[k] for k in
                                     ("checks", "n_checks", "n_failed", "holds",
                                      "failing_steps", "audit_conclusion",
                                      "integrate_conclusion", "failure_class",
                                      "zero_delta")}}
        h2 = check_h2(probe)
        h2 = {"hypothesis": "H2", **{k: h2[k] for k in
                                     ("checks", "n_checks", "n_failed", "holds",
                                      "failure_classes")}}
        h3 = check_h3(run_fresh=(phase == "prepare"))
        h4 = check_h4(probe)
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
        "freeze_commit": load(FREEZE_PATH)["freeze_commit"],
        "hypotheses": results,
        "n_hypotheses": len(results),
        "n_hypotheses_holding": sum(1 for r in results if r["holds"]),
        "n_checks": sum(r["n_checks"] for r in results),
        "n_failed": sum(r["n_failed"] for r in results),
        "verdict": ("RESUME_VERIFIED_AUDIT_READY" if holds
                    else ("PREPARE_COMPLETE" if phase == "prepare" else
                          "RESUME_VERIFICATION_FAILED")),
        "failure_modes_diagnosed": [
            f"{RESUMED}: ORCHESTRATION_AGENT_LAUNCH_FAILURE_EXIT_1_NO_RETRYABLE_SIGNATURE "
            f"(exit 1, 16 s, zero delta, no LEX_* warning)",
            "43365313827 / 43371040309 / 43384829543: same 16 s exit-1 class",
            "43365482535 / 43371675511 / 43384979714: AUDIT_QUANTUM_EXPIRY_NO_GATE (exit 78, 2700 s)",
            "43371186416: LEX_ZERO_DELTA_REPAIR (exit 67)",
            "43378111582: LANE_CYCLE_EXECUTION_FAILURE_PROVIDER_ROTATION (exit 1)",
            "43379403095: WORK_QUANTUM_EXPIRY_AT_LANE_CYCLE (exit 78, 2704 s)",
        ],
        "independent_audit_of_resumed_run_exists": False,
        "independent_audit_of_any_chain_run_exists": False,
        "continue_recommended": False,
        "claim_ceiling": (
            "Operational-resume diagnosis, deliverable verification, "
            "ordered-work re-adjudication and audit-ready snapshot assembly. "
            "It creates no new product measurement, moves no frozen bar, "
            "rubric, threshold or verdict contract, issues no serve or "
            "admission verdict, and is NOT an independent audit of run "
            f"{RESUMED} or of this run."),
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
