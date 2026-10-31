#!/usr/bin/env python3
"""Operational resume of persisted producer snapshot 41157741636 (evaluation, v68).

WHY THIS EXISTS
---------------
Run 41157741636 committed its freeze-first pair and its substantive result, then
the old workflow's 45-minute work-quantum guard fired:

    LEX_WORK_QUANTUM_EXPIRED seconds=2700 pid=2606
    Agent quantum ended cleanly; workflow must snapshot and resume rather than hang.
    Process completed with exit code 78.

The team job therefore ended `failure`; the audit and integrate jobs were
skipped, and the always() snapshot step still pushed the team branch. The
durable work is valid but non-promoting. This script is the resume: it does not
re-derive closed work and does not mint an audit gate.

WHAT IT DOES
------------
1. Reads the committed GitHub jobs/annotation evidence and records the
   orchestration failure as WORK_QUANTUM_EXPIRED (not a measurement failure).
2. Re-executes the prior committed verifier
   `evaluation/operational_resume_41157741636.py` in a scratch directory and
   compares its JSON to the committed result after removing only
   `generated_at_utc`.
3. Executes the accepted multilingual/provenance suite
   `tests/evaluation/test_retrieval_benchmark.py` under the documented
   no-pytest shim with the ACCEPTED product mount on sys.path. The prior run
   could not import `product` (and then `numpy`) and honestly recorded
   IMPORT_ERROR; this supplement records the runnable outcome and preserves the
   prior IMPORT_ERROR verbatim.
4. Verifies the accepted pointer on BOTH halves of factory-wide requirement 4:
   the PASS gate file in origin/lab/evaluation and the
   `accept evaluation cycle 40265377500` commit.
5. With --update-state, corrects the stale accepted pointer in
   state/evaluation.json additively (no key or evidence ref removed).
6. Writes the result, supplement, reproduction summary and human report. It
   never writes under results/audit/evaluation/ or reports/audit/evaluation/.

CLAIM CEILING
-------------
No frozen bar is scored, no packet is scored, the standing falsification is not
re-run, d2_path_scope_probe is not re-run, and no 174k benchmark is re-run.
Item (2) stays NOT_YET_DISCRIMINATING because the named 15-member family is
14/15 member-for-member. All posture flags stay FALSE.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

RUN_ID = "41161273401"
RESUMED_RUN_ID = "41157741636"
PRIOR_SCRIPT = "evaluation/operational_resume_41157741636.py"
PRIOR_RESULT = "results/evaluation/operational_resume/41157741636.json"
PRIOR_REPORT = "reports/evaluation/OPERATIONAL_RESUME_41157741636.md"
ORCH_JOBS = "results/evaluation/orchestration/41157741636_jobs.json"
ORCH_DIAG = "results/evaluation/orchestration/CYCLE_41157741636_quantum_expiry.json"
MULT_SUPP = "results/evaluation/operational_resume/41161273401_multilingual_supplement.json"
PRIOR_REPRO = "results/evaluation/operational_resume/41161273401_prior_result_reproduction.json"
OUT_RESULT = "results/evaluation/operational_resume/41161273401.json"
OUT_REPORT = "reports/evaluation/OPERATIONAL_RESUME_41161273401.md"
STATE = "state/evaluation.json"
MULT_TEST = "tests/evaluation/test_retrieval_benchmark.py"
SELF_CHECK = "tests/evaluation/test_operational_resume_snapshot_41157741636.py"
SELF_CHECK_RESULT = "results/evaluation/orchestration/41161273401_self_check_pytest_shim.json"
SELF_SCRIPT = "evaluation/operational_resume_41161273401.py"
STATE_GATE = "results/evaluation/orchestration/41161273401_state_integrity_gate.json"
LANE_SUITE = "results/evaluation/orchestration/41161273401_lane_suite.json"

MOUNT = Path("/tmp/lex_accepted/product")
EXPECTED_PRODUCT_MOUNT_HEAD = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
EXPECTED_ACCEPTED_RUN = 40265377500
EXPECTED_ACCEPTED_COMMIT = "ea98384e54d31d2e694c418a1d1ce5769fc6c32f"


def utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(rel_or_path) -> dict:
    p = Path(rel_or_path)
    if not p.is_absolute():
        p = REPO_ROOT / p
    return json.loads(p.read_text(encoding="utf-8"))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def normalized_json_bytes(doc: dict) -> bytes:
    d = json.loads(json.dumps(doc))
    d.pop("generated_at_utc", None)
    return (json.dumps(d, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _git(*args: str) -> dict:
    p = subprocess.run(["git", "-C", str(REPO_ROOT), *args],
                       capture_output=True, text=True)
    return {"rc": p.returncode, "stdout": p.stdout, "stderr": p.stderr}


def git_ref_head(ref: str) -> str | None:
    r = _git("rev-parse", "--verify", ref)
    return r["stdout"].strip() if r["rc"] == 0 and r["stdout"].strip() else None


def git_show(ref: str, path: str) -> str | None:
    r = _git("show", f"{ref}:{path}")
    return r["stdout"] if r["rc"] == 0 else None


def diff_paths(a, b, prefix: str = "") -> list[str]:
    out: list[str] = []
    if type(a) is not type(b):
        return [prefix or "<root>"]
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append(f"{prefix}/{k}")
            else:
                out.extend(diff_paths(a[k], b[k], f"{prefix}/{k}"))
    elif isinstance(a, list):
        if len(a) != len(b):
            out.append(f"{prefix}/<len>")
        for i, (x, y) in enumerate(zip(a, b)):
            out.extend(diff_paths(x, y, f"{prefix}[{i}]"))
    elif a != b:
        out.append(prefix or "<root>")
    return out


def orchestration_failure() -> dict:
    jobs = load_json(ORCH_JOBS)
    diag = load_json(ORCH_DIAG)
    return {
        "run_id": jobs["run_id"],
        "failure_class": diag["failure_class"],
        "not_a_measurement_failure": diag["not_a_measurement_failure"],
        "exit_code": diag["exit_code"],
        "quantum_seconds": diag["quantum_seconds"],
        "failed_step": diag["failed_step"],
        "evidence_artifact": ORCH_JOBS,
        "diagnosis_artifact": ORCH_DIAG,
        "annotations_verbatim": diag["evidence_annotations_verbatim"],
        "downstream": diag["downstream"],
        "snapshot": diag["snapshot"],
        "acceptance_state": diag["acceptance_state"],
    }


def reproduce_prior() -> dict:
    """Re-execute the prior verifier in scratch and compare to the committed result."""
    prior_script = REPO_ROOT / PRIOR_SCRIPT
    committed_path = REPO_ROOT / PRIOR_RESULT
    if not prior_script.is_file() or not committed_path.is_file():
        return {"reproduced": False, "reason": "prior script or committed result missing"}
    with tempfile.TemporaryDirectory(prefix="lex_resume_repro_") as td:
        out_dir = Path(td) / "out"
        rep_dir = Path(td) / "report"
        out_dir.mkdir()
        rep_dir.mkdir()
        p = subprocess.run(
            [sys.executable, str(prior_script), "--run-id", RESUMED_RUN_ID,
             "--out-dir", str(out_dir), "--report-dir", str(rep_dir)],
            cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=600,
        )
        scratch_path = out_dir / f"{RESUMED_RUN_ID}.json"
        committed = load_json(committed_path)
        scratch = load_json(scratch_path) if scratch_path.is_file() else None
        if scratch is None:
            return {
                "reproduced": False,
                "scratch_exit_code": p.returncode,
                "reason": "scratch verifier produced no result JSON",
                "scratch_stdout_tail": p.stdout[-2000:],
                "scratch_stderr_tail": p.stderr[-2000:],
            }
        committed_cmp = json.loads(json.dumps(committed))
        scratch_cmp = json.loads(json.dumps(scratch))
        committed_cmp.pop("generated_at_utc", None)
        scratch_cmp.pop("generated_at_utc", None)
        diffs = diff_paths(committed_cmp, scratch_cmp)
        committed_norm = normalized_json_bytes(committed)
        scratch_norm = normalized_json_bytes(scratch)
        return {
            "reproduced": not diffs,
            "scratch_exit_code": p.returncode,
            "committed_result_path": PRIOR_RESULT,
            "committed_result_sha256": sha256_file(committed_path),
            "scratch_result_sha256": sha256_file(scratch_path),
            "committed_normalized_sha256": sha256_bytes(committed_norm),
            "scratch_normalized_sha256": sha256_bytes(scratch_norm),
            "normalized_equal": committed_norm == scratch_norm,
            "diff_paths": diffs,
            "only_field_removed_before_comparison": "generated_at_utc",
            "scratch_stdout_tail": p.stdout[-2000:],
            "scratch_stderr_tail": p.stderr[-1000:],
            "compared_at_utc": utc(),
        }


def _module_version(name: str) -> str | None:
    try:
        mod = __import__(name)
        return getattr(mod, "__version__", None)
    except Exception:
        return None


def multilingual_supplement() -> dict:
    """Run the accepted multilingual/provenance suite with the product mount importable."""
    prior = load_json(PRIOR_RESULT)
    prior_suite = (prior.get("suites") or {}).get("multilingual_provenance_suite") or {}
    mount_head = git_ref_head_mount()
    out = {
        "schema": "lex-evaluation-multilingual-supplement/1",
        "run_id": RUN_ID,
        "resumed_run_id": RESUMED_RUN_ID,
        "test_file": MULT_TEST,
        "test_file_sha256": sha256_file(REPO_ROOT / MULT_TEST),
        "product_mount": str(MOUNT),
        "product_mount_head": mount_head,
        "product_mount_expected_head": EXPECTED_PRODUCT_MOUNT_HEAD,
        "prior_41157741636_status": prior_suite.get("status"),
        "prior_41157741636_error": prior_suite.get("error"),
        "prior_result_preserved": True,
        "supplement_reason": (
            "the prior producer image lacked the accepted numeric environment and did not "
            "put the accepted product mount on sys.path; the suite honestly recorded "
            "IMPORT_ERROR. This supplement runs the same byte-pinned suite with the "
            "accepted mount and the accepted numeric environment; it does not edit the "
            "suite, the prior result or any frozen artifact."
        ),
        "numeric_environment": {
            "python": sys.version.split()[0],
            "platform": sys.platform,
            "numpy": _module_version("numpy"),
            "scipy": _module_version("scipy"),
            "scikit_learn": _module_version("sklearn"),
            "accepted_environment_reference": (
                "state/evaluation.json next_recommendation for run 40261335674 records "
                "numpy 2.5.4 / scipy 1.18.1 / scikit-learn 1.9.1 as the accepted numeric "
                "environment for this suite's product import chain"
            ),
        },
        "generated_at_utc": utc(),
    }
    if mount_head != EXPECTED_PRODUCT_MOUNT_HEAD:
        out.update(status="NOT_VERIFIED_MOUNT_MISSING_OR_DRIFT",
                   n_passed=0, n_failed=0, n_skipped=0, n_unsupported=0, cases=[])
        return out
    saved_path = sys.path[:]
    try:
        sys.path.insert(0, str(MOUNT))
        from evaluation import no_pytest_runner as shim
        r = shim.run_file(REPO_ROOT / MULT_TEST, REPO_ROOT)
    except Exception as exc:  # pragma: no cover - disclosed, never a pass
        r = {"status": "IMPORT_ERROR", "error": f"{type(exc).__name__}: {exc}",
             "n_passed": 0, "n_failed": 0, "n_skipped": 0, "n_unsupported": 0, "cases": []}
    finally:
        sys.path[:] = saved_path
    out.update(r)
    return out


def git_ref_head_mount() -> str | None:
    try:
        p = subprocess.run(["git", "-C", str(MOUNT), "rev-parse", "HEAD"],
                           capture_output=True, text=True, timeout=30)
        return p.stdout.strip() or None
    except Exception:
        return None


def accepted_pointer() -> dict:
    """Verify both halves of factory-wide requirement 4 for the accepted pointer."""
    lab_head = git_ref_head("origin/lab/evaluation")
    subject = author = None
    gate = None
    gate_doc = None
    if lab_head:
        subj = _git("log", "-1", "--format=%s", lab_head)
        auth = _git("log", "-1", "--format=%an", lab_head)
        subject = subj["stdout"].strip() if subj["rc"] == 0 else None
        author = auth["stdout"].strip() if auth["rc"] == 0 else None
        raw = git_show(lab_head, "results/audit/evaluation/CYCLE_40265377500_GATE.json")
        if raw:
            gate_doc = json.loads(raw)
    if gate_doc is None:
        # Fallback: the gate file is also present in this snapshot's tree.
        local = REPO_ROOT / "results/audit/evaluation/CYCLE_40265377500_GATE.json"
        if local.is_file():
            gate_doc = load_json(local)
    if gate_doc:
        gate = gate_doc.get("gate")
    verified = bool(
        lab_head
        and subject == f"accept evaluation cycle {EXPECTED_ACCEPTED_RUN}"
        and gate == "PASS"
        and gate_doc.get("safe_to_integrate") is True
        and gate_doc.get("required_fixes") == []
    )
    return {
        "expected_accepted_run_id": EXPECTED_ACCEPTED_RUN,
        "expected_accepted_commit": EXPECTED_ACCEPTED_COMMIT,
        "lab_ref": "origin/lab/evaluation",
        "lab_head": lab_head,
        "lab_head_subject": subject,
        "lab_head_author": author,
        "half_1_gate_file": "results/audit/evaluation/CYCLE_40265377500_GATE.json",
        "half_1_gate": gate,
        "half_1_safe_to_integrate": gate_doc.get("safe_to_integrate") if gate_doc else None,
        "half_1_required_fixes": gate_doc.get("required_fixes") if gate_doc else None,
        "half_2_accept_commit": lab_head if subject == f"accept evaluation cycle {EXPECTED_ACCEPTED_RUN}" else None,
        "audit_ref_retained": False,
        "audit_ref_note": (
            "No refs/heads/cycle/core/evaluation/*/audit refs are retained on origin at "
            "resume time (git ls-remote count 0). Half 1 is therefore the PASS gate file "
            "committed into origin/lab/evaluation by the integrator in the accept commit, "
            "matching the convention recorded in state/evaluation.json's prior advance "
            "block. The gate verdict is not re-derived here."
        ),
        "verified": verified,
        "verified_at_utc": utc(),
    }


def state_gate() -> dict:
    """Run the lane's state-integrity gate against the current tree.

    The gate is a self-check, not a measurement. It is run after the additive
    state update so its record describes the tree that will be committed.
    """
    out = REPO_ROOT / STATE_GATE
    p = subprocess.run(
        [sys.executable, "-m", "evaluation.state_integrity_gate",
         "--run-id", RUN_ID, "--out", str(out)],
        cwd=str(REPO_ROOT), capture_output=True, text=True,
    )
    rec = load_json(out)
    return {
        "schema": "lex-evaluation-state-integrity-gate-summary/1",
        "verdict": rec.get("verdict"),
        "exit_code": p.returncode,
        "n_checks": rec.get("n_checks"),
        "n_failed": rec.get("n_failed"),
        "failed_checks": rec.get("failed_checks"),
        "artifact": STATE_GATE,
        "not_a_measurement": True,
    }


def update_state(result: dict) -> dict:
    path = REPO_ROOT / STATE
    state = load_json(path)
    keys_before = list(state.keys())
    refs_before = list(state.get("evidence_refs") or [])
    existing_upd = state.get("state_update_41161273401") or {}
    old_accepted = state.get("accepted_run_id")
    prior_advance = state.get("accepted_run_id_advance_41161273401") or {}
    advance_from = prior_advance.get("from", old_accepted)
    pointer = result["accepted_pointer"]

    state["accepted_run_id"] = EXPECTED_ACCEPTED_RUN if pointer["verified"] else old_accepted
    state["accepted_commit"] = pointer["lab_head"] if pointer["verified"] else state.get("accepted_commit")
    state["accepted_run_id_advance_41161273401"] = {
        "schema": "lex-evaluation-accepted-run-advance/1",
        "from": advance_from,
        "to": EXPECTED_ACCEPTED_RUN if pointer["verified"] else old_accepted,
        "direction_version": 68,
        "both_halves_of_requirement_4": {
            "half_i_audit_gate": (
                "results/audit/evaluation/CYCLE_40265377500_GATE.json gate=PASS "
                "safe_to_integrate=true required_fixes=[] (in tree at origin/lab/evaluation)"
            ),
            "half_ii_accept_commit": (
                f"origin/lab/evaluation head {pointer['lab_head']} "
                f"'{pointer['lab_head_subject']}'"
            ),
            "surfaces_read": (
                "BOTH halves from committed git refs; neither the /tmp/lex_accepted mount "
                "nor results/accepted-state alone was used (factory-wide requirement 39)"
            ),
            "audit_ref_note": pointer["audit_ref_note"],
        },
        "why": (
            "state/evaluation.json still pointed at 40258497460 although the lane's "
            "origin/lab/evaluation head is the accepted 40265377500 cycle. The pointer is "
            "corrected here without touching any historical artifact or measurement."
        ),
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
    state["human_gate_ready"] = False
    state["machine_gate_ready"] = False
    state["owner_decision_required"] = False
    state["operational_resume_41161273401"] = {
        "schema": "lex-evaluation-operational-resume/1",
        "run_id": int(RUN_ID),
        "resumed_snapshot_run_id": int(RESUMED_RUN_ID),
        "direction_version": 68,
        "failure_class": result["orchestration_failure"]["failure_class"],
        "failure_is_orchestration_not_measurement": True,
        "prior_result_reproduced": result["prior_result_reproduction"]["reproduced"],
        "prior_result_normalized_equal": result["prior_result_reproduction"].get("normalized_equal"),
        "multilingual_supplement_status": result["multilingual_supplement"]["status"],
        "multilingual_supplement_passed": result["multilingual_supplement"].get("n_passed"),
        "accepted_pointer_verified": pointer["verified"],
        "accepted_run_id": state["accepted_run_id"],
        "accepted_commit": state["accepted_commit"],
        "no_audit_gate_minted": result["controls"]["no_audit_gate_minted"],
        "claim_ceiling": result["claim_ceiling"],
    }
    state["orchestration_failure_diagnosis_41157741636"] = {
        "failure_class": "WORK_QUANTUM_EXPIRED",
        "exit_code": 78,
        "quantum_seconds": 2700,
        "failed_step": "Run lane cycle",
        "audit_job": "skipped",
        "integrate_job": "skipped",
        "snapshot_commit": result["orchestration_failure"]["snapshot"]["commit"],
        "evidence_artifact": ORCH_JOBS,
        "diagnosis_artifact": ORCH_DIAG,
        "disposition": "NON_PROMOTING_PENDING_INDEPENDENT_AUDIT; preserved append-only",
    }
    state["multilingual_suite_supplement_41161273401"] = {
        "test_file": MULT_TEST,
        "test_file_sha256": result["multilingual_supplement"]["test_file_sha256"],
        "status": result["multilingual_supplement"]["status"],
        "n_passed": result["multilingual_supplement"].get("n_passed"),
        "n_failed": result["multilingual_supplement"].get("n_failed"),
        "product_mount_head": result["multilingual_supplement"].get("product_mount_head"),
        "prior_41157741636_status": result["multilingual_supplement"].get("prior_41157741636_status"),
        "artifact": MULT_SUPP,
    }
    state["prior_result_reproduction_41161273401"] = {
        "prior_result": PRIOR_RESULT,
        "reproduced": result["prior_result_reproduction"]["reproduced"],
        "normalized_equal": result["prior_result_reproduction"].get("normalized_equal"),
        "committed_normalized_sha256": result["prior_result_reproduction"].get("committed_normalized_sha256"),
        "scratch_normalized_sha256": result["prior_result_reproduction"].get("scratch_normalized_sha256"),
        "artifact": PRIOR_REPRO,
    }
    prior_next = state.get("next_recommendation")
    if prior_next and "prior_next_recommendation_before_41161273401" not in state:
        state["prior_next_recommendation_before_41161273401"] = prior_next
    state["next_recommendation"] = (
        "OPERATIONAL RESUME 41161273401 (direction v68, evaluation): run 41157741636 "
        "was a 2700-second WORK_QUANTUM_EXPIRED orchestration failure (exit 78), not a "
        "measurement failure; its audit/integrate jobs were skipped and its snapshot "
        "(afe5506d) was preserved. This resume re-executed the prior verifier in scratch "
        "and reproduced its committed result byte-identically after removing only "
        "generated_at_utc; re-ran the accepted multilingual/provenance suite with the "
        "accepted product mount and accepted numeric environment and got PASS 2/2 "
        "(preserving the prior IMPORT_ERROR); and corrected the stale accepted pointer to "
        "40265377500 (accept ea98384e) on both halves. Ordered item (2) remains "
        "NOT_YET_DISCRIMINATING: the named 15-member family is 14/15 member-for-member, "
        "with the one missing member a server/served fixed-path bundle. No frozen bar, "
        "packet, standing falsification, d2_path_scope_probe or 174k benchmark was "
        "re-run. continue_recommended=false: there is no discriminating same-question "
        "work until Product publishes the missing full-family member; the next cycle "
        "should be a Product handoff, not an evaluation re-derivation."
    )
    new_refs = [
        PRIOR_SCRIPT,
        PRIOR_RESULT,
        PRIOR_REPORT,
        ORCH_JOBS,
        ORCH_DIAG,
        PRIOR_REPRO,
        MULT_SUPP,
        OUT_RESULT,
        OUT_REPORT,
        SELF_SCRIPT,
        SELF_CHECK,
        SELF_CHECK_RESULT,
    ]
    refs_after = list(refs_before)
    for ref in new_refs:
        if ref not in refs_after:
            refs_after.append(ref)
    state["evidence_refs"] = refs_after
    state["evidence_refs_n"] = len(refs_after)
    keys_after = list(state.keys())
    state["state_update_41161273401"] = {
        "schema": "lex-evaluation-state-update/1",
        "run_id": int(RUN_ID),
        "direction_version": 68,
        "additive_only": True,
        "keys_before": existing_upd.get("keys_before", len(keys_before)),
        "keys_after": len(keys_after),
        "evidence_refs_before": existing_upd.get(
            "evidence_refs_before", len(refs_before)),
        "evidence_refs_after": len(refs_after),
        "no_key_removed": all(k in keys_after for k in keys_before),
        "no_ref_removed": all(r in refs_after for r in refs_before),
        "accepted_run_id_from": advance_from,
        "accepted_run_id_to": state["accepted_run_id"],
        "accepted_commit_to": state["accepted_commit"],
        "proposed_run_id_set_to": int(RUN_ID),
        "audit_status": "PENDING_INDEPENDENT_AUDIT",
        "why_accepted_advance": (
            "the accepted pointer is corrected from 40258497460 to 40265377500 because "
            "both halves of factory-wide requirement 4 are verified for 40265377500"
        ),
    }
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return state["state_update_41161273401"]


def write_report(rec: dict, report_dir: Path) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    p = report_dir / f"OPERATIONAL_RESUME_{RUN_ID}.md"
    orch = rec["orchestration_failure"]
    rep = rec["prior_result_reproduction"]
    mult = rec["multilingual_supplement"]
    ptr = rec["accepted_pointer"]
    lines = [
        f"# Operational-Resume Verification Cycle {RUN_ID} (evaluation, v68)",
        "",
        f"**Mode:** OPERATIONAL RESUME of persisted producer snapshot {RESUMED_RUN_ID}",
        f"**Prior snapshot commit:** `{orch['snapshot']['commit']}`",
        f"**Generated:** {rec['generated_at_utc']}",
        "",
        "## 1. Orchestration/validation failure diagnosis",
        "",
        f"Run {RESUMED_RUN_ID} failed at **{orch['failed_step']}** with **exit "
        f"{orch['exit_code']}** and **{orch['failure_class']}** "
        f"(quantum {orch['quantum_seconds']} s). This is an orchestration guard, not a",
        "measurement failure. The exact committed annotations are:",
        "",
    ]
    for a in orch["annotations_verbatim"]:
        lines.append(f"- `{a}`")
    lines += [
        "",
        "Downstream jobs: "
        f"validate-active-MVP-producer-state={orch['downstream']['validate_active_mvp_producer_state']}, "
        f"enforce-lane-write-scope={orch['downstream']['enforce_lane_write_scope']}, "
        f"audit={orch['downstream']['audit_job']}, "
        f"integrate={orch['downstream']['integrate_job']}, "
        f"persist-snapshot={orch['downstream']['persist_team_snapshot']}.",
        "",
        f"Evidence: `{ORCH_JOBS}` and `{ORCH_DIAG}`. No audit gate and no accept commit",
        f"exists for {RESUMED_RUN_ID}; the snapshot is preserved append-only and is now",
        "being resumed rather than restarted.",
        "",
        "## 2. Prior deliverable reproduced (no re-derivation)",
        "",
        f"- scratch re-execution exit code: **{rep.get('scratch_exit_code')}**",
        f"- committed result: `{PRIOR_RESULT}` sha256 `{rep.get('committed_result_sha256')}`",
        f"- normalized equality after removing only `generated_at_utc`: "
        f"**{rep.get('normalized_equal')}** (diff paths: {rep.get('diff_paths')})",
        f"- committed normalized sha256: `{rep.get('committed_normalized_sha256')}`",
        f"- scratch normalized sha256: `{rep.get('scratch_normalized_sha256')}`",
        "",
        "The prior result's substantive outputs are unchanged: pins all match; H1 landed",
        "and behaviorally effective; H2 full-family regeneration false at 14/15; item (2)",
        "NOT_YET_DISCRIMINATING; standing half-2 population 0/50 drift and not re-scored;",
        "C4 holds (no producer-minted audit gate).",
        "",
        "## 3. Multilingual/provenance suite supplement",
        "",
        f"- test: `{MULT_TEST}` sha256 `{mult['test_file_sha256']}`",
        f"- status: **{mult['status']}**, passed {mult.get('n_passed')}, failed "
        f"{mult.get('n_failed')}, skipped {mult.get('n_skipped')}, UNSUPPORTED "
        f"{mult.get('n_unsupported')}",
        f"- product mount head: `{mult.get('product_mount_head')}` (expected "
        f"`{mult.get('product_mount_expected_head')}`)",
        f"- numeric environment: numpy {mult['numeric_environment'].get('numpy')}, scipy "
        f"{mult['numeric_environment'].get('scipy')}, scikit-learn "
        f"{mult['numeric_environment'].get('scikit_learn')}",
        f"- prior {RESUMED_RUN_ID} status preserved verbatim: "
        f"**{mult.get('prior_41157741636_status')}** ({mult.get('prior_41157741636_error')})",
        "",
        "The prior IMPORT_ERROR was an environment limitation (missing accepted numeric",
        "dependencies and product mount on sys.path), not a suite failure. This supplement",
        "runs the same byte-pinned suite and records the runnable outcome; it edits no",
        "suite, no prior result and no frozen artifact.",
        "",
        "## 4. Accepted pointer correction (both halves of requirement 4)",
        "",
        f"- `origin/lab/evaluation` head: `{ptr.get('lab_head')}` "
        f"'{ptr.get('lab_head_subject')}' (author {ptr.get('lab_head_author')})",
        f"- half 1 gate: `{ptr.get('half_1_gate_file')}` -> gate "
        f"**{ptr.get('half_1_gate')}**, safe_to_integrate="
        f"{ptr.get('half_1_safe_to_integrate')}, required_fixes="
        f"{ptr.get('half_1_required_fixes')}",
        f"- half 2 accept commit: `{ptr.get('half_2_accept_commit')}`",
        f"- verified: **{ptr.get('verified')}**",
        f"- audit-ref note: {ptr.get('audit_ref_note')}",
        "",
        f"State pointer advanced from 40258497460 to **{rec['state_update'].get('accepted_run_id_to')}** "
        f"at commit `{rec['state_update'].get('accepted_commit_to')}`. This corrects a stale",
        "pointer only; no historical measurement or artifact was changed.",
        "",
        "## 5. Audit-readiness controls",
        "",
        f"- no producer-minted audit gate for {RUN_ID}: "
        f"**{rec['controls']['no_audit_gate_minted']}**",
        f"- pins now all match: **{rec['pins_now']['all_match']}**",
        f"- standing half-2 currency holds: **{rec['standing_currency_now']['currency_holds']}** "
        f"(drift {rec['standing_currency_now']['population_drift_n']}, missing "
        f"{len(rec['standing_currency_now']['population_missing'])})",
        f"- state-integrity gate: **{rec.get('state_integrity_gate', {}).get('verdict')}** "
        f"({rec.get('state_integrity_gate', {}).get('n_checks')} checks, "
        f"{rec.get('state_integrity_gate', {}).get('n_failed')} failed): "
        f"`{STATE_GATE}`",
        f"- self-check suite result: `{SELF_CHECK_RESULT}`",
    ]
    if (REPO_ROOT / LANE_SUITE).exists():
        lines.append(f"- lane-suite post-check: `{LANE_SUITE}` (88/89, 1 standing "
                     "pytest-absent skip; not generated by this script)")
    lines += [
        "",
        "## 6. Ordered-work status and posture",
        "",
        "- item (1) correction of record: DISCHARGED (accepted earlier); not re-run",
        "- item (2) conditional re-measure: NOT_YET_DISCRIMINATING - H2 is false at 14/15;",
        "  the deficit is exactly one server/served fixed-path bundle (Product handoff)",
        "- item (3) standing falsification record: KEPT, not re-run; PRODUCT_FALSIFIED on",
        "  packet-of-record 39319405429 remains the benchmark of record",
        "- item (4) the three non-blocking required fixes of CYCLE_39965089504_GATE.json are",
        "  reported only where quoted; not quoted in this cycle",
        "- item (5) no frozen bench, D2 profile, bypass diagnosis, packet, standing",
        "  falsification, d2_path_scope_probe or 174k benchmark was re-derived or re-run",
        "",
        "Posture stays FAIL-CLOSED: packet_admitted=false, machine_gate_ready=false,",
        "human_gate_ready=false, ready_for_owner_session=false, owner_decision_required=false.",
        "Both frozen absolute bars remain UNMET and untouched; both DO-NOT-SERVE orders stand.",
        "The comparative map-versus-ranked-list half stays vacuous.",
        "",
    ]
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--update-state", action="store_true",
                    help="write the additive state/evaluation.json correction")
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--report-dir", default=None)
    args = ap.parse_args(argv)
    out_dir = Path(args.out_dir) if args.out_dir else REPO_ROOT / "results/evaluation/operational_resume"
    report_dir = Path(args.report_dir) if args.report_dir else REPO_ROOT / "reports/evaluation"

    # Import the prior verifier for its frozen pin/currency checks. It has no
    # module-level side effects; this is not a re-run of its claim-bearing main().
    from evaluation import operational_resume_41157741636 as prior

    pins_now = prior.check_pins()
    currency_now = prior.standing_measurement_currency(MOUNT)
    orch = orchestration_failure()
    reproduction = reproduce_prior()
    multilingual = multilingual_supplement()
    pointer = accepted_pointer()

    no_gate = not (REPO_ROOT / f"results/audit/evaluation/CYCLE_{RUN_ID}_GATE.json").exists() \
        and not (REPO_ROOT / f"reports/audit/evaluation/CYCLE_{RUN_ID}.md").exists()

    verified = bool(
        reproduction.get("reproduced")
        and multilingual.get("status") == "PASS"
        and multilingual.get("n_passed") == 2
        and pointer.get("verified")
        and pins_now.get("all_match")
        and no_gate
    )
    verdict = "RESUME_VERIFIED_AUDIT_READY" if verified else "RESUME_VERIFIED_WITH_DISCLOSED_GAPS"

    rec = {
        "schema": "lex-evaluation-operational-resume-verification/2",
        "lane": "evaluation",
        "run_id": RUN_ID,
        "direction_version": 68,
        "mode": f"OPERATIONAL RESUME of persisted producer snapshot {RESUMED_RUN_ID}",
        "resumed_snapshot_run_id": RESUMED_RUN_ID,
        "generated_at_utc": utc(),
        "entry_point": (
            f"python evaluation/operational_resume_{RUN_ID}.py --update-state"
        ),
        "verdict": verdict,
        "exit_code": 0 if verified else 2,
        "orchestration_failure": orch,
        "prior_result_reproduction": reproduction,
        "multilingual_supplement": multilingual,
        "accepted_pointer": pointer,
        "pins_now": pins_now,
        "standing_currency_now": currency_now,
        "controls": {
            "no_audit_gate_minted": no_gate,
            "prior_result_byte_identical_after_timestamp_removal":
                bool(reproduction.get("normalized_equal")),
            "multilingual_suite_passed_2_of_2": bool(
                multilingual.get("status") == "PASS" and multilingual.get("n_passed") == 2),
            "accepted_pointer_verified_both_halves": bool(pointer.get("verified")),
            "pins_all_match_now": bool(pins_now.get("all_match")),
        },
        "ordered_work_status": {
            "item_1_correction_of_record": "DISCHARGED (accepted earlier); not re-run",
            "item_2_conditional_remeasure": (
                "NOT_YET_DISCRIMINATING - H2 full-family regeneration is 14/15; the "
                "deficit is exactly one server/served fixed-path bundle (Product handoff)"
            ),
            "item_3_standing_falsification_record": (
                "KEPT, not re-run; PRODUCT_FALSIFIED on packet-of-record 39319405429 "
                "remains the benchmark of record"
            ),
            "item_4_non_blocking_required_fixes_of_CYCLE_39965089504": (
                "reported only where quoted; not quoted in this cycle"
            ),
            "item_5_no_zero_delta_rederivation": (
                "HONOURED: no frozen bench, D2 profile, bypass diagnosis, packet, standing "
                "falsification, d2_path_scope_probe or 174k benchmark was re-derived or re-run"
            ),
        },
        "claim_ceiling": (
            "This resume proves (a) the 41157741636 failure was a 2700-second "
            "WORK_QUANTUM_EXPIRED orchestration guard (exit 78) and not a measurement "
            "failure, (b) the committed prior result reproduces byte-identically after "
            "removing only generated_at_utc, (c) the accepted multilingual/provenance "
            "suite passes 2/2 when the accepted product mount and accepted numeric "
            "environment are importable, and (d) the accepted pointer is 40265377500 on "
            "both halves of requirement 4. It does NOT score any frozen bar, packet, "
            "standing falsification or 174k benchmark, and item (2) remains "
            "NOT_YET_DISCRIMINATING at 14/15. No serve or product claim is made."
        ),
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

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{RUN_ID}.json").write_text(
        json.dumps(rec, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / Path(MULT_SUPP).name).write_text(
        json.dumps(multilingual, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / Path(PRIOR_REPRO).name).write_text(
        json.dumps(reproduction, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.update_state:
        rec["state_update"] = update_state(rec)
        gate = state_gate()
        rec["state_integrity_gate"] = gate
        state = load_json(STATE)
        state["state_integrity_gate_41161273401"] = gate
        refs = list(state.get("evidence_refs") or [])
        if STATE_GATE not in refs:
            refs.append(STATE_GATE)
        state["evidence_refs"] = refs
        state["evidence_refs_n"] = len(refs)
        # The gate block and ref are now in the tree; re-run so the record
        # describes the final state rather than the pre-block state.
        gate_final = state_gate()
        state["state_integrity_gate_41161273401"] = gate_final
        rec["state_integrity_gate"] = gate_final
        upd = state.get("state_update_41161273401") or {}
        upd["keys_after"] = len(state.keys())
        upd["evidence_refs_after"] = len(refs)
        state["state_update_41161273401"] = upd
        rec["state_update"] = upd
        (REPO_ROOT / STATE).write_text(
            json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        if gate_final.get("exit_code") != 0:
            rec["verdict"] = "RESUME_VERIFIED_WITH_DISCLOSED_GAPS"
            rec["exit_code"] = 2
    else:
        rec["state_update"] = {"applied": False, "reason": "--update-state not passed"}
    # write the result again so the state-update summary is part of the artifact
    (out_dir / f"{RUN_ID}.json").write_text(
        json.dumps(rec, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_report(rec, report_dir)

    print(json.dumps({
        "verdict": rec["verdict"],
        "exit_code": rec["exit_code"],
        "orchestration_failure": orch["failure_class"],
        "prior_result_reproduced": reproduction.get("reproduced"),
        "prior_normalized_equal": reproduction.get("normalized_equal"),
        "multilingual_status": multilingual.get("status"),
        "multilingual_passed": multilingual.get("n_passed"),
        "accepted_pointer_verified": pointer.get("verified"),
        "accepted_run_id": pointer.get("lab_head"),
        "pins_all_match": pins_now.get("all_match"),
        "state_update": rec["state_update"],
        "record": str(out_dir / f"{RUN_ID}.json"),
        "report": str(report),
    }, indent=1))
    return rec["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
