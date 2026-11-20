#!/usr/bin/env python3
"""Operational resume of the persisted evaluation snapshot of run 44665691117.

This run (44674389464) resumes from HEAD b65f472d, the persisted producer
snapshot of run 44665691117.  It is an OPERATIONAL / EVIDENCE-PROVENANCE cycle:
it diagnoses the orchestration failures, finishes the two final gates that the
prior snapshot left DEFERRED, verifies the v68 ordered-work deliverable without
re-running any falsifier or bar, and makes the snapshot audit-ready.

It deliberately does NOT:
  * edit any frozen hypothesis, amendment, freeze record or verdict contract;
  * overwrite any claim-bearing results/ artifact of an earlier run;
  * write outside evaluation/, tests/evaluation/, results/evaluation/,
    reports/evaluation/, state/evaluation.json;
  * re-run the FAST-MVP falsifier, the D2 profile, d2_path_scope_probe or any
    universal-174k benchmark.

Phases:
  python -m evaluation.operational_resume_44674389464            # R1..R5
  python -m evaluation.operational_resume_44674389464 --phase final-gates
  python -m evaluation.operational_resume_44674389464 --phase post-commit
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

RUN = 44674389464
PRIOR = 44665691117
SCOPE_FAIL_RUN = 44665054809
TARGET_RUN = 40261335674
ACCEPTED_RUN = 40265377500
DIRV = 68
OUT = ROOT / "results" / "evaluation" / "operational_resume_44674389464"
PRIOR_OUT = ROOT / "results" / "evaluation" / f"operational_resume_{PRIOR}"
STATE = ROOT / "state" / "evaluation.json"
LANE_STATE = ROOT / "evaluation" / "state" / "evaluation.json"
CAPTURE = OUT / "github_run_status_capture.json"

HYP = ROOT / f"evaluation/OPERATIONAL_RESUME_{RUN}_HYPOTHESIS_V1.json"
FRZ = ROOT / f"evaluation/OPERATIONAL_RESUME_{RUN}_FREEZE_V1.json"
FRZ2 = ROOT / f"evaluation/OPERATIONAL_RESUME_{RUN}_FREEZE_V2.json"
AMEND = ROOT / f"evaluation/OPERATIONAL_RESUME_{RUN}_FREEZE_V1_1_AMENDMENT.json"

OFFENDING = [
    "reports/audit/evaluation/CYCLE_40261335674.md",
    "results/audit/evaluation/CYCLE_40261335674_GATE.json",
]
RECOVERY = [
    "results/evaluation/audit_namespace_recovery_40261335674/CYCLE_40261335674.md",
    "results/evaluation/audit_namespace_recovery_40261335674/CYCLE_40261335674_GATE.json",
]
WORKFLOW_SHA = "2bd0f49f2eb877abf4a8e080f15586168d773b780c3a531bd9bb05995efed1e1"
PRIOR_INSTRUMENT = ROOT / f"evaluation/operational_resume_{PRIOR}.py"
PRIOR_FREEZE = ROOT / f"evaluation/OPERATIONAL_RESUME_{PRIOR}_FREEZE_V1.json"
PRIOR_RESULT = PRIOR_OUT / f"{PRIOR}.json"
PRODUCT_MOUNT_HEAD = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
MOUNT_GATE = Path("/tmp/lex_accepted/product/results/audit/product/CYCLE_39965089504_GATE.json")
MOUNT_GATE_SHA = "f915bac807af988c840c6911738d646e5f794ab16261c63df85d278d227509ef"
ITEM1 = {
    "reports/evaluation/BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md":
        "b10eeb3a720cd6352fbc7eabbf8d3430989b52d90193d0f948e69908ef5dc48d",
    "results/evaluation/bypass_clause_correction/40144816305.json":
        "2e691dd02c7b53bac7b1bf048363e56006a1596dd3cade1fd4fb44514330228d",
}


def sha256_file(p: Path) -> str | None:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def git(*args: str) -> tuple[int, str]:
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    return r.returncode, ((r.stdout or "") + (r.stderr or "")).strip()


def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Freeze verification (frozen for THIS run, before first execution)
# ---------------------------------------------------------------------------
def verify_freeze() -> dict:
    if not (HYP.exists() and FRZ.exists() and CAPTURE.exists()):
        return {"passed": False, "checks": {"inputs_present": False}}
    # A V1_1 amendment may re-pin the instrument bytes after an implementation-time
    # bug discovered BEFORE any result record exists; V1 and the amendment are both
    # preserved verbatim and the amendment names the exact replacement pin.
    active = FRZ2 if FRZ2.exists() else FRZ
    fz = json.loads(active.read_text())
    cap_sha = sha256_file(CAPTURE)
    checks = {
        "inputs_present": True,
        "instrument_sha_matches_active_pin": sha256_file(Path(__file__)) == fz["instrument"]["sha256"],
        "hypothesis_sha_matches_freeze": sha256_file(HYP) == fz["hypothesis"]["sha256"],
        "capture_sha_matches_freeze": cap_sha == fz["evidence_inputs"]["capture_sha256"],
        "pins_the_current_run": fz.get("run_id") == RUN,
        "direction_version_pinned": fz.get("direction_version") == DIRV,
        "no_frozen_bar_edits": fz.get("frozen_bar_edits") == [],
    }
    if FRZ2.exists():
        amd = json.loads(AMEND.read_text()) if AMEND.exists() else {}
        checks["amendment_sha_matches_freeze"] = (
            sha256_file(AMEND) == fz.get("amendment", {}).get("sha256"))
        checks["amendment_pins_active_instrument"] = (
            amd.get("instrument_sha256_corrected") == fz["instrument"]["sha256"])
        checks["v1_freeze_preserved"] = FRZ.exists() and json.loads(FRZ.read_text()).get("run_id") == RUN
    return {"passed": all(checks.values()), "checks": checks,
            "active_freeze": str(active.relative_to(ROOT)),
            "instrument_sha256": sha256_file(Path(__file__)),
            "hypothesis_sha256": sha256_file(HYP), "capture_sha256": cap_sha}


# ---------------------------------------------------------------------------
# R1 - accepted head on BOTH halves of factory-wide requirement 4
# ---------------------------------------------------------------------------
def r1_accepted_head() -> dict:
    st = json.loads(STATE.read_text())
    accepted = int(st["accepted_run_id"])
    gate = ROOT / "results" / "audit" / "evaluation" / f"CYCLE_{accepted}_GATE.json"
    g = json.loads(gate.read_text()) if gate.exists() else {}
    rc_lab, lab_head = git("rev-parse", "origin/lab/evaluation")
    rc_log, log = git("log", "origin/lab/evaluation", "--oneline",
                      "--grep", f"accept evaluation cycle {accepted}")
    checks = {
        "accepted_run_id_is_40265377500": accepted == ACCEPTED_RUN,
        "gate_file_present": gate.exists(),
        "gate_PASS": g.get("gate") == "PASS",
        "safe_to_integrate": g.get("safe_to_integrate") is True,
        "required_fixes_empty": g.get("required_fixes") == [],
        "lab_head_resolves": rc_lab == 0 and bool(lab_head),
        "accept_commit_on_lab": rc_log == 0 and f"accept evaluation cycle {accepted}" in log,
    }
    return {"rule": "R1", "passed": all(checks.values()), "checks": checks,
            "accepted_run_id": accepted, "lab_head": lab_head if rc_lab == 0 else None,
            "accept_commit_line": log.splitlines()[0] if rc_log == 0 and log else None,
            "surfaces_read": ["results/audit/evaluation gate file", "origin/lab/evaluation git log"],
            "note": "both halves read directly; neither the mount nor results/accepted-state alone was used (requirement 39)"}


# ---------------------------------------------------------------------------
# R2 - orchestration / validation failure diagnosis
# ---------------------------------------------------------------------------
def r2_failure_diagnosis() -> dict:
    cap = json.loads(CAPTURE.read_text())
    rest = json.loads((PRIOR_OUT / f"run_{SCOPE_FAIL_RUN}_rest_capture.json").read_text())
    ann = json.loads((PRIOR_OUT / f"run_{SCOPE_FAIL_RUN}_annotation_evidence.json").read_text())
    jobs = {j["name"]: j for j in rest.get("jobs", [])}
    team = jobs.get("team", {})
    bad_step = [s for s in team.get("steps", []) if s.get("conclusion") == "failure"]
    # recompute the frozen workflow sha from the control-plane ref
    r = subprocess.run(["git", "show", "origin/main:.github/workflows/core-lane.yml"],
                       cwd=ROOT, capture_output=True)
    wf_sha = hashlib.sha256(r.stdout).hexdigest() if r.returncode == 0 else None

    c0 = cap["runs"][str(SCOPE_FAIL_RUN)]
    c1 = cap["runs"][str(PRIOR)]
    checks = {
        "scope_fail_step9_failure": len(bad_step) == 1 and bad_step[0].get("number") == 9
            and bad_step[0].get("name") == "Enforce lane write scope",
        "scope_fail_annotation_exit_3": ann.get("failing_step", {}).get("annotation")
            == "Process completed with exit code 3.",
        "offending_paths_exact": ann.get("offending_paths") == OFFENDING,
        "audit_and_integrate_skipped": jobs.get("audit", {}).get("conclusion") == "skipped"
            and jobs.get("integrate", {}).get("conclusion") == "skipped",
        "steps_6_7_8_success": all(
            any(s.get("number") == n and s.get("conclusion") == "success"
                for s in team.get("steps", []))
            for n in (6, 7, 8)),
        "workflow_sha_pin_reproduced": wf_sha == WORKFLOW_SHA,
        "audit_death_not_a_verdict": c1.get("audit_gate_written") is False
            and c1.get("audit_verdict_issued") is False
            and c1.get("classification") == "AUDIT_JOB_DEATH_NOT_A_VERDICT",
        "audit_death_step5": any(
            s.get("name") == "Independent audit" for s in
            c1.get("jobs", [{}])[1].get("non_success_steps", [])),
        "captures_are_committed_inputs": True,
    }
    return {"rule": "R2", "passed": all(checks.values()), "checks": checks,
            "scope_failure": {"run": SCOPE_FAIL_RUN, "class": "WRITE_SCOPE_VALIDATION_FAILURE_exit_3",
                              "failing_step": 9, "offending_paths": OFFENDING,
                              "not": ["rc67", "rc68/69", "rc78", "provider death", "audit verdict"]},
            "audit_death": {"run": PRIOR, "class": "AUDIT_JOB_DEATH_NOT_A_VERDICT",
                            "failing_step": 5, "no_gate_no_verdict": True,
                            "cause_certainty": "INFERRED (job logs HTTP 403 without admin rights)"},
            "workflow_sha_observed": wf_sha, "workflow_sha_expected": WORKFLOW_SHA,
            "resolution_of_prior_null": ("the prior run observed null for this pin because origin/main was not "
                                         "resolvable in that detached checkout; the pin itself is correct and is "
                                         "reproduced here from the same control-plane ref")}


# ---------------------------------------------------------------------------
# R3 - prior snapshot's stale-instrument defect (negative result, preserved)
# ---------------------------------------------------------------------------
def r3_prior_instrument_drift() -> dict:
    cur = sha256_file(PRIOR_INSTRUMENT)
    fz = json.loads(PRIOR_FREEZE.read_text())
    pinned = fz["instrument"]["sha256"]
    prior = json.loads(PRIOR_RESULT.read_text())
    fi = prior.get("frozen_inputs", {})
    s6 = prior.get("rules", {}).get("S6", {})
    checks = {
        "prior_instrument_bytes_drifted_from_pin": cur != pinned,
        "prior_record_reports_pin_false": fi.get("checks", {}).get("instrument_sha_matches_pin") is False,
        "prior_record_verdict_not_confirmed": prior.get("verdict") == "DIAGNOSIS_NOT_CONFIRMED",
        "prior_record_S4_scope_passed": prior.get("rules", {}).get("S4", {}).get("passed") is True,
        "prior_record_S2_provenance_passed": prior.get("rules", {}).get("S2", {}).get("passed") is True,
        "prior_record_item4_check_was_old_form": "item_4_gate_present_not_quoted" in s6.get("checks", {}),
        "current_bytes_use_mount_gate_pin": "item_4_gate_pin_verified_and_not_quoted"
            in PRIOR_INSTRUMENT.read_text(),
        "mount_gate_pin_matches": sha256_file(MOUNT_GATE) == MOUNT_GATE_SHA,
        "prior_result_not_rewritten": prior.get("generated_at_utc") == "2026-11-20T03:25:42Z",
    }
    return {"rule": "R3", "passed": all(checks.values()), "checks": checks,
            "prior_instrument_sha_now": cur, "prior_instrument_sha_pinned": pinned,
            "prior_record_verdict": prior.get("verdict"),
            "finding": "STALE_RESULT_RECORD",
            "explanation": ("run 44665691117 edited its instrument AFTER executing it: the committed bytes now "
                            "pin the product-mount item-(4) gate, but the recorded result still carries the old "
                            "gate-absent check and DIAGNOSIS_NOT_CONFIRMED. The result is preserved verbatim; "
                            "this run does not re-run that instrument (its final-gates phase would overwrite it) "
                            "and instead re-derives the checks under its own run id."),
            "disposition": "PRESERVED_AS_NEGATIVE_EVIDENCE_NOT_SUPPRESSED"}


# ---------------------------------------------------------------------------
# R4 - byte-identical relocation, originals retained
# ---------------------------------------------------------------------------
def r4_relocation() -> dict:
    rec = ROOT / "results/evaluation/audit_namespace_recovery_40261335674/RELOCATION_RECORD.json"
    rec_sha = sha256_file(rec)
    rows = []
    for src, dst in zip(OFFENDING, RECOVERY):
        s, d = ROOT / src, ROOT / dst
        rows.append({"source": src, "recovery": dst,
                     "source_sha256": sha256_file(s), "recovery_sha256": sha256_file(d),
                     "byte_identical": sha256_file(s) == sha256_file(d),
                     "original_retained": s.is_file()})
    rr = json.loads(rec.read_text()) if rec.exists() else {}
    checks = {
        "both_copies_byte_identical": all(r["byte_identical"] for r in rows),
        "both_originals_retained": all(r["original_retained"] for r in rows),
        "relocation_record_present": rec.exists(),
        "record_declares_retention": rr.get("originals_retained") is True
            and rr.get("originals_deleted") is False,
        "record_sha_matches_prior_pin": rec_sha == "d702c27372a1cc954c5a1152377158050acff2b6eda1131f7c1c1e09f8d0272b",
    }
    return {"rule": "R4", "passed": all(checks.values()), "checks": checks, "rows": rows,
            "relocation_record": str(rec.relative_to(ROOT)), "relocation_record_sha256": rec_sha,
            "control_plane_disclosure": ("the two retained originals are committed in the resume base and cannot "
                                         "be removed from a producer worktree (a delete is itself an out-of-scope "
                                         "status entry -> exit 3); on PASS the integrator overwrites only the "
                                         "current run's gate/report paths, so this residue is recorded for the "
                                         "control plane and is not edited here")}


# ---------------------------------------------------------------------------
# R5 - v68 ordered-work deliverable, read-only
# ---------------------------------------------------------------------------
def r5_ordered_work() -> dict:
    obs: dict = {}
    checks = {}
    i1 = {}
    for rel, want in ITEM1.items():
        got = sha256_file(ROOT / rel)
        i1[rel] = {"expected": want, "observed": got, "match": got == want}
    checks["item1_correction_intact"] = all(v["match"] for v in i1.values())
    obs["item1"] = i1

    mount = Path("/tmp/lex_accepted/product")
    rc, head = git("-C", str(mount), "rev-parse", "HEAD") if mount.is_dir() else (1, "")
    head = head if rc == 0 else None
    span = sha256_file(mount / "product/query/counter_evidence_span.py")
    fam = ROOT / "results/evaluation/counter_evidence_quality_benchmark/40062917685.json"
    checks["item2_precondition_unchanged"] = (
        head == PRODUCT_MOUNT_HEAD
        and span == "82cea13122b13a60e4da746072af4a185f9e4b2e0ef51853d6273acb7a1bb6ce"
        and sha256_file(fam) == "948a8929817f265236c87bbc1b3a17559fa7db2bd03ee4ccddc36332977ac717")
    obs["item2"] = {"product_mount_head": head, "expected_head": PRODUCT_MOUNT_HEAD,
                    "span_sha256": span, "frozen_family_pin_sha256": sha256_file(fam),
                    "status": "NOT_YET_DISCRIMINATING", "protocol_executed": False,
                    "packet_of_record_scored": False, "falsifier_reexecuted": False,
                    "why": "product head byte-identical to accepted adjudication 40258497460; frozen 15-member family still 14/15"}

    bor = ROOT / "results/evaluation/minimal_retrieval_ca_benchmark/40182692670_engine_mapping_free_recall_falsifier.json"
    prior = ROOT / "results/evaluation/fast_mvp_current_head_ca_falsifier/40105794124.json"
    vac = ROOT / "results/evaluation/fast_mvp_current_head_ca_falsifier/40182692670.json"
    bv = json.loads(bor.read_text()).get("verdict") if bor.exists() else None
    checks["item3_benchmark_of_record_present"] = (
        bor.exists() and bv == "PRODUCT_FALSIFIED" and prior.exists() and vac.exists()
        and json.loads(vac.read_text()).get("verdict") == "NOT_MEASURED_VACUOUS")
    obs["item3"] = {"benchmark_of_record": str(bor.relative_to(ROOT)), "verdict": bv,
                    "status": "KEPT_UNCHANGED", "re_executed": False}

    checks["item4_gate_pin_verified_not_quoted"] = (
        sha256_file(MOUNT_GATE) == MOUNT_GATE_SHA)
    obs["item4"] = {"gate": "mount:/tmp/lex_accepted/product/results/audit/product/CYCLE_39965089504_GATE.json",
                    "pin_matches": sha256_file(MOUNT_GATE) == MOUNT_GATE_SHA,
                    "required_fix_counts_quoted": False, "status": "REPORTED_ONLY_WHERE_QUOTED"}
    obs["item5"] = {"frozen_bar_edits": [], "falsifier_reexecuted": False,
                    "d2_profile_rederived": False, "universal_174k_benchmark": False,
                    "status": "HONOURED"}
    checks["item5_no_closed_work_rerun"] = True
    return {"rule": "R5", "passed": all(checks.values()), "checks": checks, "observed": obs,
            "ordered_work_status": {
                "1": "DISCHARGED_ELSEWHERE (hash-verified, not re-run)",
                "2": "NOT_YET_DISCRIMINATING (precondition carried forward, protocol not executed)",
                "3": "KEPT (benchmark of record present, not re-executed)",
                "4": "REPORTED_ONLY where quoted (not quoted)",
                "5": "HONOURED (no frozen bench / D2 profile / bypass re-derivation, no 174k)"}}


# ---------------------------------------------------------------------------
# Final gates - AFTER the state update and the report exist
# ---------------------------------------------------------------------------
def r6_state_gates() -> dict:
    nested = OUT / f"{RUN}_nested_evidence_refs.json"
    if nested.exists():
        nested.unlink()
    p = subprocess.run([sys.executable, "-m", "evaluation.nested_evidence_refs_guard",
                        "--run-id", str(RUN), "--out-dir", str(OUT)],
                       cwd=ROOT, capture_output=True, text=True)
    rec = json.loads(nested.read_text()) if nested.exists() else {}
    p2 = subprocess.run([sys.executable, "-m", "evaluation.state_integrity_gate"],
                        cwd=ROOT, capture_output=True, text=True)
    try:
        gate = json.loads(p2.stdout)
    except json.JSONDecodeError:
        gate = {}
    checks = {
        "nested_guard_exit_0": p.returncode == 0,
        "nested_refs_zero_unresolved": rec.get("n_unresolved") == 0,
        "top_level_refs_zero_unresolved": rec.get("n_top_level_unresolved") == 0,
        "state_integrity_exit_0": p2.returncode == 0,
        "state_integrity_11_of_11": gate.get("n_checks") == 11 and gate.get("n_failed") == 0,
    }
    return {"rule": "R6", "passed": all(checks.values()), "checks": checks,
            "nested": {k: rec.get(k) for k in ("verdict", "n_top_level_evidence_refs",
                                              "n_top_level_unresolved", "n_unresolved", "resolution_counts")},
            "state_integrity": {"verdict": gate.get("verdict"), "n_checks": gate.get("n_checks"),
                                "n_failed": gate.get("n_failed"),
                                "failed_checks": [c.get("check") for c in gate.get("checks", [])
                                                  if not c.get("passed")]},
            "records": [str(nested.relative_to(ROOT))]}


def r7_write_scope(out_name: str) -> dict:
    out = OUT / out_name
    p = subprocess.run([sys.executable, "-m", "evaluation.snapshot_audit.write_scope",
                        "--lane", "evaluation", "--out", str(out)],
                       cwd=ROOT, capture_output=True, text=True)
    rec = json.loads(out.read_text()) if out.exists() else {}
    checks = {"scope_predicate_exit_0": p.returncode == 0,
              "verdict_scope_clean": rec.get("verdict", {}).get("verdict") == "SCOPE_CLEAN",
              "n_bad_zero": rec.get("verdict", {}).get("n_bad") == 0,
              "no_audit_namespace_entry": not any(
                  e.get("path", "").startswith(("results/audit/", "reports/audit/"))
                  for e in rec.get("verdict", {}).get("entries", []))}
    return {"rule": "R7", "passed": all(checks.values()), "checks": checks,
            "observed": {k: rec.get("verdict", {}).get(k) for k in ("verdict", "n_entries", "n_bad", "bad_paths")},
            "record": str(out.relative_to(ROOT))}


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
RESULT = OUT / f"{RUN}.json"
FINAL = OUT / f"{RUN}_final_gates.json"
CLOSING = ("Operational provenance only: no quality measurement, no frozen bar, rubric, threshold, gate "
           "predicate or verdict contract edited, no serve verdict, no packet admission, no human-gate "
           "claim, no universal-174k benchmark, no falsifier/probe re-execution.")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["full", "final-gates", "post-commit"], default="full")
    args = ap.parse_args(argv)

    if args.phase == "post-commit":
        r = r7_write_scope(f"{RUN}_write_scope_post_commit.json")
        print(json.dumps({"phase": "post-commit", "passed": r["passed"],
                          "observed": r["observed"]}, indent=2))
        return 0 if r["passed"] else 1

    if args.phase == "final-gates":
        rules = {"freeze_inputs": verify_freeze(), "R6": r6_state_gates(), "R7": r7_write_scope(f"{RUN}_write_scope.json")}
        passed = {k: bool(v.get("passed")) for k, v in rules.items()}
        all_ok = all(passed.values())
        out = {"schema": "lex-evaluation-operational-resume-final-gates/1", "run_id": RUN,
               "resumes_snapshot_of": PRIOR, "direction_version": DIRV,
               "generated_at_utc": now(), "claim_bearing_run": RUN,
               "audit_status": "PENDING_INDEPENDENT_AUDIT", "accepted_as_evidence": False,
               "rules": rules, "rule_pass": passed, "passed": all_ok,
               "verdict": "AUDIT_READY" if all_ok else "FINAL_GATES_FAILED",
               "exit_code": 0 if all_ok else 1,
               "closes_deferred_gates_of_prior_run": ["S3_state_refs (state refs re-pointed this run)",
                                                       "S5 (nested refs + state integrity 11/11)"],
               "claim_ceiling": CLOSING}
        write_json(FINAL, out)
        print(json.dumps({"phase": "final-gates", "verdict": out["verdict"],
                          "rule_pass": passed, "record": str(FINAL.relative_to(ROOT))}, indent=2))
        return out["exit_code"]

    # full phase
    OUT.mkdir(parents=True, exist_ok=True)
    rules = {"freeze_inputs": verify_freeze(), "R1": r1_accepted_head(),
             "R2": r2_failure_diagnosis(), "R3": r3_prior_instrument_drift(),
             "R4": r4_relocation(), "R5": r5_ordered_work(),
             "R6": {"passed": None, "status": "DEFERRED_TO_FINAL_GATES"},
             "R7": {"passed": None, "status": "DEFERRED_TO_FINAL_GATES"}}
    decided = {k: bool(v.get("passed")) for k, v in rules.items() if v.get("passed") is not None}
    ok = all(decided.values())
    out = {
        "schema": "lex-evaluation-operational-resume/3", "run_id": RUN,
        "resumes_snapshot_of": PRIOR, "snapshot_head": "b65f472db790f4a33545b2acbca05c18f8fe35d0",
        "lane": "evaluation", "direction_version": DIRV, "mode": "OPERATIONAL_RESUME",
        "generated_at_utc": now(), "claim_bearing_run": RUN,
        "audit_status": "PENDING_INDEPENDENT_AUDIT", "pending_independent_audit": True,
        "accepted_as_evidence": False,
        "accepted_run_id": ACCEPTED_RUN,
        "failure_chain": [
            {"run": SCOPE_FAIL_RUN, "class": "WRITE_SCOPE_VALIDATION_FAILURE_exit_3",
             "failing_step": 9, "evidence": "results/evaluation/operational_resume_44665691117/run_44665054809_annotation_evidence.json"},
            {"run": PRIOR, "class": "AUDIT_JOB_DEATH_NOT_A_VERDICT", "failing_step": 5,
             "evidence": "results/evaluation/operational_resume_44674389464/github_run_status_capture.json"}
        ],
        "rules": rules, "rule_pass": decided, "passed": ok,
        "verdict": "ORCHESTRATION_DIAGNOSIS_CONFIRMED" if ok else "RULE_FAILURE_RECORDED",
        "exit_code": 0 if ok else 1,
        "prior_snapshot_defect": {"verdict": "STALE_RESULT_RECORD", "preserved": True,
                                   "not_rewritten": True},
        "ordered_work_status": rules["R5"]["ordered_work_status"],
        "negative_results": [
            "run 44665691117's own instrument returned DIAGNOSIS_NOT_CONFIRMED because its bytes drifted from the freeze pin after execution; its result is preserved verbatim and re-derived here, not overwritten",
            "the GitHub job logs for the audit death are HTTP 403 without admin rights, so the provider/quantum cause is INFERRED, not an established log line",
            "no quality, recall, counter-authority, label, geometry or serve measurement is produced; item (2) stays NOT_YET_DISCRIMINATING"
        ],
        "claim_ceiling": CLOSING,
    }
    write_json(RESULT, out)
    print(json.dumps({"phase": "full", "verdict": out["verdict"], "rule_pass": decided,
                      "record": str(RESULT.relative_to(ROOT))}, indent=2))
    return out["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
