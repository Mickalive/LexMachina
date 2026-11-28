#!/usr/bin/env python3
"""Operational-resume instrument for evaluation run 46106181686.

Resumes the persisted producer snapshot of run 46100599319 (commit 39784cc0):
diagnoses the orchestration failure, verifies the frozen deliverable without
re-running it, and emits audit-readiness records. This instrument NEVER writes
results/audit/** or reports/audit/** -- those are the independent auditor's.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "results" / "evaluation" / "operational_resume_46106181686"
RESUME_RUN = 46106181686
SUBJECT_RUN = 46100599319
SNAPSHOT = "39784cc02d5eb06915cab32bfc5e2647631de74a"
HYP = "evaluation/OPERATIONAL_RESUME_46106181686_HYPOTHESIS_V1.json"
FREEZE = "evaluation/OPERATIONAL_RESUME_46106181686_FREEZE_V1.json"
RESULT = "results/evaluation/fast_mvp_retrieval_recall_benchmark/46100599319.json"
COMPARISON = "results/evaluation/fast_mvp_retrieval_recall_benchmark/46100599319_COMPARISON_prior.json"
CLAIM_RECOMPUTE = "results/evaluation/orchestration/46100599319_claim_recompute.json"
STATE_BLOCK = "fast_mvp_retrieval_recall_benchmark_46100599319"

ROOT_STATE = REPO / "state" / "evaluation.json"
LANE_STATE = REPO / "evaluation" / "state" / "evaluation.json"
ALLOWED_PREFIXES = ("evaluation/", "tests/evaluation/", "results/evaluation/",
                    "reports/evaluation/", "data/evaluation/")


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha(path: str | Path) -> str:
    return hashlib.sha256((REPO / path).read_bytes()).hexdigest() if not Path(path).is_absolute() else hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path: str | Path):
    return json.loads((REPO / path).read_text(encoding="utf-8"))


def dump(path: str | Path, obj: dict) -> str:
    p = REPO / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return sha(p)


def in_scope(path: str) -> bool:
    return path == "state/evaluation.json" or path.startswith(ALLOWED_PREFIXES)


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, text=True,
                          capture_output=True).stdout.strip()


# --------------------------------------------------------------------------
# 1. Orchestration diagnosis, from pinned public API envelopes + git refs
# --------------------------------------------------------------------------
def diagnose() -> dict:
    run = load("results/evaluation/operational_resume_46106181686/api/run_46100599319_api.json")
    jobs = load("results/evaluation/operational_resume_46106181686/api/jobs_46100599319_api.json")
    rows = {}
    for j in jobs["jobs"]:
        rows[j["name"]] = {
            "id": j["id"], "status": j["status"], "conclusion": j["conclusion"],
            "started_at": j.get("started_at"), "completed_at": j.get("completed_at"),
            "steps": [{"number": s["number"], "name": s["name"],
                       "conclusion": s.get("conclusion")} for s in j.get("steps", [])],
        }
    team, audit = rows["team"], rows["audit"]
    team_steps = {s["name"]: s["conclusion"] for s in team["steps"]}
    failing = [s["name"] for s in audit["steps"] if s["conclusion"] == "failure"]
    skipped = [s["name"] for s in audit["steps"] if s["conclusion"] == "skipped"]
    gate_path = REPO / f"results/audit/evaluation/CYCLE_{SUBJECT_RUN}_GATE.json"
    report_path = REPO / f"reports/audit/evaluation/CYCLE_{SUBJECT_RUN}.md"
    audit_refs = git("for-each-ref", "--format=%(refname)",
                     f"refs/remotes/origin/cycle/core/evaluation/{SUBJECT_RUN}/audit")
    from datetime import datetime as _dt
    dur = (_dt.fromisoformat(audit["completed_at"].replace("Z", "+00:00"))
           - _dt.fromisoformat(audit["started_at"].replace("Z", "+00:00"))).total_seconds()
    return {
        "schema": "lex-evaluation-operational-resume-diagnosis/1",
        "lane": "evaluation", "direction_version": 68,
        "generated_at_utc": now(), "resume_run_id": RESUME_RUN,
        "subject_run_id": SUBJECT_RUN, "producer_snapshot_commit": SNAPSHOT,
        "run_envelope": {"path": "results/evaluation/operational_resume_46106181686/api/run_46100599319_api.json",
                         "sha256": sha("results/evaluation/operational_resume_46106181686/api/run_46100599319_api.json"),
                         "conclusion": run["conclusion"], "run_number": run["run_number"]},
        "jobs_envelope": {"path": "results/evaluation/operational_resume_46106181686/api/jobs_46100599319_api.json",
                          "sha256": sha("results/evaluation/operational_resume_46106181686/api/jobs_46100599319_api.json")},
        "jobs": rows,
        "established_facts": {
            "team_conclusion": team["conclusion"],
            "team_validation_step": team_steps.get("Validate active MVP producer state"),
            "team_scope_step": team_steps.get("Enforce lane write scope"),
            "audit_conclusion": audit["conclusion"],
            "audit_failing_steps": failing,
            "audit_skipped_steps": skipped,
            "audit_duration_seconds": dur,
            "integrate_conclusion": rows["integrate"]["conclusion"],
            "resilience_conclusion": rows["resilience"]["conclusion"],
            "audit_gate_file_in_tree": gate_path.exists(),
            "audit_report_file_in_tree": report_path.exists(),
            "audit_branch_refs": audit_refs.splitlines(),
            "job_logs_http_status_unauthenticated": 403,
        },
        "root_cause": {
            "classification": "AUDIT_AGENT_STEP_FAILURE_NOT_A_VERDICT",
            "statement": "The team job and its scope/state validation steps passed and force-persisted the producer snapshot; the audit job died inside the 'Independent audit' agent step, so the gate read and audit-snapshot push never ran and integrate was skipped.",
            "cause_status": "NOT_ESTABLISHED",
            "hedged_cause": "The exact agent exit cause cannot be established: job logs return HTTP 403 unauthenticated and no gate or auditor commit exists. The 46-minute step duration is consistent with the documented provider/model-failure or agent-quantum class (factory-wide requirement index 16), but that is an inference, not an observed log line.",
        },
        "not_a": ["independent audit verdict", "product defect", "frozen-bar result",
                  "serve verdict", "human decision", "scope violation"],
        "disposition": "Operational resume on the unchanged snapshot; no restart, no re-derivation, no frozen edit.",
        "claim_ceiling": "Orchestration state only. Establishes that run 46100599319 failed after a successful, scope-clean producer cycle, inside the independent-audit agent step, with no gate or audit branch; it does not score the product or promote any claim.",
    }


# --------------------------------------------------------------------------
# 2. Deliverable verification, from committed bytes only (no re-measurement)
# --------------------------------------------------------------------------
def verify_deliverable() -> dict:
    state = load(ROOT_STATE)
    block = state[STATE_BLOCK]
    result = load(RESULT)
    checks: dict[str, bool] = {}

    pin_pairs = {
        "subject_hypothesis_pin": ("evaluation/FAST_MVP_RETRIEVAL_RECALL_BENCHMARK_46100599319_HYPOTHESIS_V1.json",
                                   block["hypothesis"]["sha256"]),
        "subject_freeze_pin": ("evaluation/FAST_MVP_RETRIEVAL_RECALL_BENCHMARK_46100599319_FREEZE_V1.json",
                               block["freeze_record"]["sha256"]),
        "instrument_pin": ("evaluation/fast_mvp_retrieval_recall_benchmark.py", block["instrument_sha256"]),
        "result_pin": (RESULT, block["result"]["sha256"]),
    }
    hashes = {name: sha(path) for name, (path, _exp) in pin_pairs.items()}
    for name, (_path, exp) in pin_pairs.items():
        checks[f"{name}_matches_state"] = hashes[name] == exp

    resume_freeze = load(FREEZE)
    subject_freeze = load("evaluation/FAST_MVP_RETRIEVAL_RECALL_BENCHMARK_46100599319_FREEZE_V1.json")
    checks["resume_freeze_hypothesis_hash_matches"] = (
        resume_freeze["frozen_inputs"]["hypothesis_sha256_at_freeze"] == sha(HYP))
    checks["api_envelopes_hash_match_resume_freeze"] = (
        resume_freeze["frozen_inputs"]["api_run_envelope_sha256"] == sha("results/evaluation/operational_resume_46106181686/api/run_46100599319_api.json")
        and resume_freeze["frozen_inputs"]["api_jobs_envelope_sha256"] == sha("results/evaluation/operational_resume_46106181686/api/jobs_46100599319_api.json"))
    checks["resume_freeze_precedes_verification"] = resume_freeze["frozen_at_utc"] < now()

    # artifacts added by the snapshot commit all resolve, and none is out of scope
    added = [p for p in git("show", "--name-only", "--format=", SNAPSHOT).splitlines() if p]
    missing = [p for p in added if not (REPO / p).is_file()]
    bad_scope = [p for p in added if not in_scope(p)]
    checks["all_snapshot_files_present"] = not missing
    checks["snapshot_scope_clean"] = not bad_scope

    # independent recomputation of the 16 claim-recompute checks
    bres = block["result"]
    cl = result["claim"]
    agg = cl["aggregate"]
    recomputed = {
        "verdict_matches_state": result["verdict"] == bres["verdict"],
        "exit_matches_state": result["exit_code"] == bres["exit_code"],
        "head_matches_state": result["product_mount_head"] == block["product_mount_head"],
        "direction_v68": result["direction_version"] == 68 == block["direction_version"],
        "network_calls_zero": result["network_calls"] == 0 == bres["network_calls"],
        "no_174k": result["no_174k_benchmark_rerun"] is True,
        "input_hits": agg["all"]["input_hits"] == bres["aggregate"]["input_hits"] == 17,
        "product_hits": agg["all"]["product_hits"] == bres["aggregate"]["product_hits"] == 15,
        "denominator": agg["all"]["present_denominator"] == bres["aggregate"]["present_denominator"] == 18,
        "baseline_hits": agg["baseline"]["input_hits"] == bres["baseline_channel"]["input_hits"] == 5
                         and agg["baseline"]["product_hits"] == bres["baseline_channel"]["product_hits"] == 3,
        "counter_hits": agg["counter"]["input_hits"] == bres["counter_channel"]["input_hits"] == 12
                        and agg["counter"]["product_hits"] == bres["counter_channel"]["product_hits"] == 12,
        "n_discriminating": cl["n_discriminating_cells"] == bres["n_discriminating_cells"] == 10,
        "n_not_measured": cl["n_cells_not_measured"] == bres["n_cells_not_measured"] == 14,
        "n_controls": result["n_controls"] == bres["n_controls"] == 10,
        "n_controls_passed": result["n_controls_passed"] == bres["n_controls_passed"] == 9,
        "failed_controls_empty": result["failed_controls"] == [] == bres["failed_controls"],
        "no_new_thresholds": result["no_new_thresholds"] is True,
    }
    recompute_artifact = load(CLAIM_RECOMPUTE)
    checks["claim_recompute_16of16"] = all(recomputed.values()) and all(recompute_artifact["checks"].values())

    # freeze-before-execution ordering and unchanged frozen inputs (subject run)
    freeze_t = subject_freeze["freeze_recorded_at_utc"]
    checks["subject_freeze_precedes_execution"] = freeze_t < result["generated_at_utc"]
    checks["frozen_inputs_unchanged"] = (
        result["rehash_before_execution"]["hypothesis_matches_freeze_pin"] is True
        and result["rehash_before_execution"]["spec_matches_pin"] is True
        and result["rehash_after_execution"]["spec_unchanged"] is True
        and result["rehash_after_execution"]["hypothesis_unchanged"] is True)

    # report/result agreement on headline numbers
    report = (REPO / block["report"]).read_text(encoding="utf-8")
    report_tokens = ["PRODUCT_FALSIFIED_RECALL_LOSS", "7be4480e", "network_calls=0",
                     "24 cells", "10 discriminating", "input_hits 17", "product_hits 15",
                     "baseline `5 \u2192 3`", "counter `12 \u2192 12`", "C7b"]
    checks["report_agrees_with_result"] = all(t in report for t in report_tokens)

    # test suite artifacts: summary matches the underlying shims
    suites = {}
    for key, path in (
        ("multilingual", "results/evaluation/orchestration/46100599319_pytest_shim_multilingual.json"),
        ("recall", "results/evaluation/orchestration/46100599319_pytest_shim_recall.json"),
        ("ca", "results/evaluation/orchestration/46100599319_pytest_shim_ca.json"),
        ("lane", "results/evaluation/lane_suite/46100599319.json"),
    ):
        d = load(path)
        suites[key] = {"path": path, "sha256": sha(path),
                       "verdict": d.get("verdict", d.get("overall_pass")),
                       "passed": d.get("n_passed"),
                       "failed": d.get("n_failed"),
                       "skipped": d.get("n_skipped"),
                       "unsupported": d.get("n_unsupported", 0)}
    checks["suites_match_state_block"] = (
        suites["multilingual"]["passed"] == 2 and suites["recall"]["passed"] == 7
        and suites["ca"]["passed"] == 14 and suites["ca"]["unsupported"] == 1
        and suites["lane"]["passed"] == 88)

    return {
        "schema": "lex-evaluation-deliverable-verification/1",
        "lane": "evaluation", "direction_version": 68,
        "generated_at_utc": now(), "resume_run_id": RESUME_RUN,
        "subject_run_id": SUBJECT_RUN, "subject_snapshot_commit": SNAPSHOT,
        "method": "committed-byte re-hash and cross-artifact recomputation ONLY; no re-execution of the frozen benchmark or falsifier",
        "snapshotted_files": added, "snapshotted_files_missing": missing,
        "snapshotted_files_out_of_scope": bad_scope,
        "pins": {k: {"path": v[0], "observed_sha256": hashes[k], "expected_sha256": v[1]} for k, v in pin_pairs.items()},
        "other_artifact_sha256": {
            "comparison": sha(COMPARISON), "claim_recompute": sha(CLAIM_RECOMPUTE),
            "report": sha(block["report"]),
        },
        "recomputed_claim_checks": recomputed,
        "claim_recompute_artifact_all_pass": all(recompute_artifact["checks"].values()),
        "freeze_ordering": {
            "subject_freeze_at_utc": freeze_t,
            "subject_result_generated_at_utc": result["generated_at_utc"],
            "resume_freeze_at_utc": resume_freeze["frozen_at_utc"],
            "resume_verification_at_utc": now(),
        },
        "suites": suites,
        "checks": checks,
        "verdict": "DELIVERABLE_VERIFIED" if all(checks.values()) else "DELIVERABLE_NOT_VERIFIED",
        "failures": [k for k, v in checks.items() if not v],
        "claim_ceiling": "Confirms the persisted 46100599319 artifacts are complete, pinned and internally consistent. It is not a new measurement, does not re-score the product, and does not promote the pending run to accepted evidence.",
    }


# --------------------------------------------------------------------------
# 3. Audit-readiness gate runners
# --------------------------------------------------------------------------
def run_gate(out_rel: str) -> dict:
    cp = subprocess.run([sys.executable, "-B", "-m", "evaluation.state_integrity_gate",
                         "--run-id", str(RESUME_RUN), "--out", out_rel],
                        cwd=REPO, text=True, capture_output=True)
    try:
        rec = json.loads((REPO / out_rel).read_text(encoding="utf-8"))
    except Exception:
        rec = {"stdout": cp.stdout, "stderr": cp.stderr}
    rec["exit_code"] = cp.returncode
    return rec


def run_nested() -> dict:
    out_dir = f"results/evaluation/operational_resume_{RESUME_RUN}/nested_refs_final"
    cp = subprocess.run([sys.executable, "-B", "evaluation/nested_evidence_refs_guard.py",
                         "--run-id", str(RESUME_RUN), "--out-dir", out_dir],
                        cwd=REPO, text=True, capture_output=True)
    p = REPO / out_dir / f"{RESUME_RUN}_nested_evidence_refs.json"
    rec = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"stdout": cp.stdout, "stderr": cp.stderr}
    rec["exit_code"] = cp.returncode
    return rec


def run_scope(out_rel: str) -> dict:
    cp = subprocess.run([sys.executable, "-B", "-m", "evaluation.snapshot_audit.write_scope",
                         "--lane", "evaluation", "--out", out_rel],
                        cwd=REPO, text=True, capture_output=True)
    p = REPO / out_rel
    rec = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"stdout": cp.stdout, "stderr": cp.stderr}
    rec["exit_code"] = cp.returncode
    return rec


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "verify"
    if mode == "verify":
        diag = diagnose()
        ver = verify_deliverable()
        dg = dump(f"results/evaluation/operational_resume_{RESUME_RUN}/diagnosis_{SUBJECT_RUN}.json", diag)
        vg = dump(f"results/evaluation/operational_resume_{RESUME_RUN}/deliverable_verification_{SUBJECT_RUN}.json", ver)
        pre = run_gate(f"results/evaluation/operational_resume_{RESUME_RUN}/state_integrity_gate_{RESUME_RUN}_pre.json")
        print(json.dumps({"diagnosis": diag["root_cause"]["classification"],
                          "deliverable": ver["verdict"], "deliverable_failures": ver["failures"],
                          "pre_state_gate": pre.get("verdict"),
                          "pre_state_gate_failures": pre.get("failed_checks"),
                          "diagnosis_sha256": dg, "verification_sha256": vg}, indent=2))
        return 0
    if mode == "finalize":
        final_gate = run_gate(f"results/evaluation/operational_resume_{RESUME_RUN}/state_integrity_gate_{RESUME_RUN}_final.json")
        post_gate = run_gate(f"results/evaluation/operational_resume_{RESUME_RUN}/state_integrity_gate_{RESUME_RUN}_post.json")
        nested = run_nested()
        scope = run_scope(f"results/evaluation/operational_resume_{RESUME_RUN}/write_scope_{RESUME_RUN}_final.json")
        root, lane = load(ROOT_STATE), load(LANE_STATE)
        rec = {
            "schema": "lex-evaluation-audit-readiness-final/1",
            "lane": "evaluation", "direction_version": 68,
            "generated_at_utc": now(), "resume_run_id": RESUME_RUN,
            "subject_run_id": SUBJECT_RUN,
            "state_integrity_gate_final": final_gate,
            "state_integrity_gate_post_write": post_gate,
            "nested_evidence_refs": nested,
            "pre_existing_nested_unresolved": {
                "count": nested.get("n_unresolved", 0),
                "items": nested.get("unresolved", []),
                "introduced_by_this_resume": False,
                "disposition": "The surviving annotated historical ref under github_run_advance_40246705199 is preserved verbatim and disclosed, not fabricated into existence or deleted; top-level evidence_refs are fully resolved.",
            },
            "write_scope": scope,
            "state_identity": {
                "root": {k: root.get(k) for k in ("accepted_run_id", "direction_version", "github_run",
                                                  "proposed_run_id", "evidence_refs_n", "audit_status")},
                "lane": {k: lane.get(k) for k in ("accepted_run_id", "direction_version", "github_run",
                                                  "proposed_run_id", "evidence_refs_n", "audit_status")},
                "root_refs_len": len(root["evidence_refs"]),
                "lane_refs_len": len(lane["evidence_refs"]),
                "new_resume_block_present": f"operational_resume_{RESUME_RUN}" in root,
            },
            "posture": {k: root.get(k, False) for k in ("human_gate_ready", "machine_gate_ready",
                                                        "ready_for_owner_session", "owner_decision_required",
                                                        "packet_admitted")},
        }
        rec["all_pass"] = (
            final_gate.get("verdict") == "ALL_CHECKS_PASS"
            and post_gate.get("verdict") == "ALL_CHECKS_PASS"
            and scope.get("exit_code") == 0
            and nested.get("n_top_level_unresolved") == 0
            and len(root["evidence_refs"]) == root["evidence_refs_n"]
            and len(lane["evidence_refs"]) == lane["evidence_refs_n"]
            and rec["state_identity"]["new_resume_block_present"]
            and all(v is False for v in rec["posture"].values()))
        rec["verdict"] = "AUDIT_READY_PENDING_INDEPENDENT_AUDIT" if rec["all_pass"] else "NOT_AUDIT_READY"
        sh = dump(f"results/evaluation/operational_resume_{RESUME_RUN}/audit_readiness_{RESUME_RUN}.json", rec)
        print(json.dumps({"audit_readiness": rec["verdict"], "all_pass": rec["all_pass"],
                          "record_sha256": sh, "final_gate": final_gate.get("verdict"),
                          "post_gate": post_gate.get("verdict"),
                          "scope": scope.get("verdict", scope.get("status")),
                          "nested": nested.get("verdict")}, indent=2))
        return 0 if rec["all_pass"] else 1
    print(f"usage: {sys.argv[0]} verify|finalize", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
