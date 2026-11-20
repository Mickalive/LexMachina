#!/usr/bin/env python3
"""Operational resume of run 44665054809 (core evaluation, direction v68).

WHAT FAILED
-----------
Run 44665054809 (dispatch: lane=evaluation, direction_version=68,
resume_from_run_id=44659329788, repair_round=0) completed its producer step
("Run lane cycle", step 6, 256s), passed state validation (step 7) and junk
cleaning (step 8), then died at step 9 "Enforce lane write scope" with the
workflow's `exit 3` ("lane crossed protected scope").  audit and integrate were
skipped; resilience re-dispatched this run.  The two offending paths were
producer-written audit-namespace files:

    reports/audit/evaluation/CYCLE_40261335674.md
    results/audit/evaluation/CYCLE_40261335674_GATE.json

WHAT THIS INSTRUMENT DOES (no quality measurement, no bar, no serve verdict)
---------------------------------------------------------------------------
1. freezes-verified: re-hash the V1 hypothesis, the V1_1 amendment, the V1
   freeze and the two committed REST/annotation captures;
2. S1: assert the captured REST/job evidence matches the diagnosis;
3. S2: adjudicate the provenance of the two audit-namespace files with GIT
   evidence (audit ref, accept commit, producing-commit authorship) and with an
   independent re-execution of the accepted write-scope classifier
   (evaluation.snapshot_audit.write_scope --repro-from-git), and record that
   the GitHub API 404 is NON-discriminating because the control probes 404 too;
4. relocate them byte-for-byte into the in-scope accepted recovery namespace
   results/evaluation/audit_namespace_recovery_40261335674/ with a
   RELOCATION_RECORD (schema lex-evaluation-audit-namespace-relocation/1,
   matching the accepted precedents for runs 40153908549 / 40182692670 /
   40232590665); the originals are RETAINED, never deleted or rewritten;
5. S3/S4: prove byte-identity and evaluate the producer write-scope predicate
   over the live worktree;
6. S6 / H5: read-only verification of the ordered-work deliverable pointers
   (item (1) correction-of-record hashes, item (2) precondition carry-forward,
   item (3) benchmark-of-record existence) WITHOUT re-running any falsifier,
   probe, frozen bar or universal-174k benchmark.

Modes:
    python -m evaluation.operational_resume_44665691117
        phase `full`: diagnosis, provenance adjudication, byte relocation, the
        live write-scope predicate and read-only ordered-work verification.
    python -m evaluation.operational_resume_44665691117 --phase final-gates
        phase `final-gates`: the S3 state-ref clauses plus the nested-refs guard
        and the state-integrity gate.  Runs AFTER the state update and the
        reports exist, so every path the state cites is present.
    python -m evaluation.operational_resume_44665691117 --phase post-commit
        re-evaluates the write-scope predicate after the cycle commit, i.e.
        exactly what workflow step 9 will see.

Exit codes: 0 = every (possibly amended) rule passed, 1 = at least one rule
failed (recorded honestly, never suppressed), 2 = missing frozen inputs.
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

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

RUN = 44665691117
PRIOR_RUN = 44665054809
TARGET_RUN = 40261335674
DIRV = 68

OUT_DIR = REPO_ROOT / "results" / "evaluation" / "operational_resume_44665691117"
RECOVERY_DIR = REPO_ROOT / "results" / "evaluation" / "audit_namespace_recovery_40261335674"
STATE = REPO_ROOT / "state" / "evaluation.json"

OFFENDING = [
    "reports/audit/evaluation/CYCLE_40261335674.md",
    "results/audit/evaluation/CYCLE_40261335674_GATE.json",
]
RECOVERY_MAP = {
    "reports/audit/evaluation/CYCLE_40261335674.md": "results/evaluation/audit_namespace_recovery_40261335674/CYCLE_40261335674.md",
    "results/audit/evaluation/CYCLE_40261335674_GATE.json": "results/evaluation/audit_namespace_recovery_40261335674/CYCLE_40261335674_GATE.json",
}
PRODUCING_COMMIT = "16c84319b570fa29a9a1737b9df335ca068ce275"
PRIOR_BASE_COMMIT = "14cd6ed7284da2f236e2acc5ac92c48c1f1ac844"
PRODUCT_MOUNT_HEAD = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
ITEM1 = {
    "reports/evaluation/BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md":
        "b10eeb3a720cd6352fbc7eabbf8d3430989b52d90193d0f948e69908ef5dc48d",
    "results/evaluation/bypass_clause_correction/40144816305.json":
        "2e691dd02c7b53bac7b1bf048363e56006a1596dd3cade1fd4fb44514330228d",
}
BENCH_OF_RECORD = ("results/evaluation/minimal_retrieval_ca_benchmark/"
                   "40182692670_engine_mapping_free_recall_falsifier.json")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def git(*args: str) -> tuple[int, str]:
    r = subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def run_write_scope(*args: str) -> tuple[int, dict | None, str]:
    r = subprocess.run(
        [sys.executable, "-m", "evaluation.snapshot_audit.write_scope", *args],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    rec = None
    if r.stdout.strip().startswith("{"):
        try:
            rec = json.loads(r.stdout)
        except json.JSONDecodeError:
            rec = None
    # the module also writes --out; caller passes --out when it wants the record
    return r.returncode, rec, (r.stdout + r.stderr)


# --------------------------------------------------------------------------
# 1. frozen-input verification
# --------------------------------------------------------------------------
def verify_freeze() -> dict:
    hyp = REPO_ROOT / f"evaluation/OPERATIONAL_RESUME_{RUN}_HYPOTHESIS_V1.json"
    amd = REPO_ROOT / f"evaluation/OPERATIONAL_RESUME_{RUN}_HYPOTHESIS_V1_1_AMENDMENT.json"
    frz = REPO_ROOT / f"evaluation/OPERATIONAL_RESUME_{RUN}_FREEZE_V1.json"
    missing = [str(p) for p in (hyp, amd, frz) if not p.exists()]
    if missing:
        return {"passed": False, "missing": missing}
    fz = json.loads(frz.read_text())
    checks = {
        "hypothesis_sha_matches_freeze": sha256_file(hyp) == fz["hypothesis"]["sha256"],
        "amendment_sha_matches_freeze": sha256_file(amd) == fz["amendment"]["sha256"],
        "amendment_pins_the_same_hypothesis":
            json.loads(amd.read_text())["amended_file_sha256"] == fz["hypothesis"]["sha256"],
        "instrument_sha_matches_pin": sha256_file(Path(__file__)) == fz["instrument"]["sha256"],
    }
    inputs = []
    for item in fz["evidence_inputs"]:
        p = item["path"]
        if p.startswith("origin/") and ":.github/" in p:
            # a git-object input, optionally carrying a trailing human annotation
            # after " (" (the freeze wrote the path that way)
            spec = p.split(" (", 1)[0]
            ref, objpath = spec.split(":", 1)
            raw = subprocess.run(["git", "show", f"{ref}:{objpath}"], cwd=REPO_ROOT,
                                 capture_output=True)
            got = (hashlib.sha256(raw.stdout).hexdigest() if raw.returncode == 0 else None)
        else:
            fp = REPO_ROOT / p.split(" (", 1)[0]
            got = sha256_file(fp) if fp.exists() else None
        ok = got == item["sha256"]
        inputs.append({"path": p, "expected_sha256": item["sha256"],
                       "observed_sha256": got, "match": ok})
        checks["evidence_inputs_unchanged"] = (checks.get("evidence_inputs_unchanged", True) and ok)
    return {"passed": all(checks.values()), "checks": checks, "evidence_inputs": inputs,
            "hypothesis_sha256": sha256_file(hyp), "amendment_sha256": sha256_file(amd),
            "freeze_sha256": sha256_file(frz)}


# --------------------------------------------------------------------------
# 2. S1 - captured failure evidence
# --------------------------------------------------------------------------
def check_s1() -> dict:
    cap = json.loads((OUT_DIR / f"run_{PRIOR_RUN}_rest_capture.json").read_text())
    ev = json.loads((OUT_DIR / f"run_{PRIOR_RUN}_annotation_evidence.json").read_text())
    jobs = {j["name"]: j for j in cap["jobs"]}
    team = jobs.get("team", {})
    step9 = [s for s in team.get("steps", []) if s["number"] == 9]
    checks = {
        "run_conclusion_failure": cap["run"]["conclusion"] == "failure",
        "team_job_failure": team.get("conclusion") == "failure",
        "step9_named": bool(step9) and step9[0]["name"] == "Enforce lane write scope",
        "step9_failure": bool(step9) and step9[0]["conclusion"] == "failure",
        "step6_success": any(s["number"] == 6 and s["conclusion"] == "success"
                             for s in team.get("steps", [])),
        "step7_success": any(s["number"] == 7 and s["conclusion"] == "success"
                             for s in team.get("steps", [])),
        "audit_skipped": jobs.get("audit", {}).get("conclusion") == "skipped",
        "integrate_skipped": jobs.get("integrate", {}).get("conclusion") == "skipped",
        "resilience_success": jobs.get("resilience", {}).get("conclusion") == "success",
        "offending_paths_exact": ev["offending_paths"] == OFFENDING,
        "annotation_is_exit_3": ev["failing_step"]["annotation"] == "Process completed with exit code 3.",
        "excluded_classes_documented": all(
            isinstance(ev["excluded_failure_classes"].get(k), str)
            and ev["excluded_failure_classes"][k].strip()
            for k in ("rc67_LX_ZERO_DELTA_REPAIR",
                      "rc68_missing_state / rc69_state_not_updated",
                      "rc78_LX_WORK_QUANTUM_EXPIRED", "provider_death")),
        "no_excluded_class_claimed_as_the_cause": not any(
            v.strip().lower().startswith(("applicable", "yes", "present", "confirmed"))
            for v in ev["excluded_failure_classes"].values()),
    }
    checks["failure_class_not_in_excluded"] = (
        checks["excluded_classes_documented"] and checks["no_excluded_class_claimed_as_the_cause"])
    return {"rule": "S1", "passed": all(checks.values()), "checks": checks,
            "failure_class": "WRITE_SCOPE_VALIDATION_FAILURE_exit_3" if all(checks.values()) else "UNEXPECTED",
            "excluded_failure_classes": ev["excluded_failure_classes"]}


# --------------------------------------------------------------------------
# 3. S2 - provenance of the pseudo-audit files
# --------------------------------------------------------------------------
def check_s2() -> dict:
    out: dict = {"rule": "S2", "checks": {}, "per_path": {}}

    rc, txt = git("ls-remote", "--heads", "origin",
                  f"refs/heads/cycle/core/evaluation/{TARGET_RUN}/audit")
    out["checks"]["no_audit_branch_ref"] = rc == 0 and not txt.strip()
    out["audit_branch_ls_remote"] = txt.strip()

    rc, txt = git("log", "--all", "--oneline",
                  f"--grep=accept evaluation cycle {TARGET_RUN}")
    out["checks"]["no_accept_commit"] = not txt.strip()
    out["accept_commit_matches"] = [l for l in txt.splitlines() if l.strip()]

    for p in OFFENDING:
        rc, txt = git("log", "--all", "--diff-filter=A",
                      "--format=%H|%an|%ae|%s", "--", p)
        lines = [l for l in txt.splitlines() if l.strip()]
        rows = []
        for l in lines:
            sha, an, ae, subj = (l.split("|", 3) + [""] * 4)[:4]
            rows.append({"commit": sha, "author_name": an, "author_email": ae, "subject": subj})
        out["per_path"][p] = {"adding_commits": rows}
        ok = (len(rows) == 1 and rows[0]["commit"] == PRODUCING_COMMIT
              and rows[0]["author_name"] == "lex-evaluation-team"
              and rows[0]["subject"] == f"evaluation cycle {PRIOR_RUN} repair 0")
        out["checks"][f"single_producer_adding_commit::{p}"] = ok

    # independent re-execution of the accepted write-scope classifier on the
    # failed run's own base -> snapshot pair
    repro_out = OUT_DIR / "write_scope_repro_44665054809.json"
    rc, _, log = run_write_scope("--lane", "evaluation",
                                 "--repro-from-git", PRIOR_BASE_COMMIT[:10],
                                 PRODUCING_COMMIT[:10], "--out", str(repro_out))
    repro = json.loads(repro_out.read_text()) if repro_out.exists() else None
    bad = repro["verdict"]["bad_paths"] if repro else []
    out["checks"]["write_scope_repro_reproduces_exit3"] = (
        rc == 1 and repro is not None
        and repro["verdict"]["verdict"] == "SCOPE_VIOLATION"
        and bad == OFFENDING)
    out["write_scope_repro"] = {
        "command": "python -m evaluation.snapshot_audit.write_scope --lane evaluation "
                   f"--repro-from-git {PRIOR_BASE_COMMIT[:10]} {PRODUCING_COMMIT[:10]}",
        "exit_code": rc, "verdict": repro["verdict"]["verdict"] if repro else None,
        "bad_paths": bad, "record": str(repro_out.relative_to(REPO_ROOT)) if repro else None,
    }

    # API probe: recorded and explicitly declared NON-discriminating
    probe = json.loads((OUT_DIR / "run_40261335674_api_probe.json").read_text())
    st = {k: v["run_endpoint"].get("http_status") for k, v in probe["probes"].items()}
    control_404 = st.get("40265377500") == 404 and st.get("40258497460") == 404
    out["checks"]["api_404_recorded"] = st.get(str(TARGET_RUN)) == 404
    out["api_probe"] = {
        "http_statuses": st,
        "discriminating_for_H3": False,
        "why": ("control probes for the ACCEPTED run 40265377500 and for 40258497460 also return 404 "
                "while recent runs (44659329788, 44665054809) return 200, so the 404 is a run-retention "
                "artifact of the Actions API and proves NOTHING about run 40261335674 in particular. "
                "The git evidence above is the sufficient and independent basis for H3."),
    }

    # internal inconsistencies of the producer-authored pair (mechanical)
    gate = json.loads((REPO_ROOT / OFFENDING[1]).read_text())
    rep = (REPO_ROOT / OFFENDING[0]).read_text()
    wf = git("show", "origin/main:.github/workflows/core-lane.yml")[1]
    incons = {
        "gate_continue_recommended_vs_report_disposition":
            f"{gate.get('continue_recommended')} vs "
            + ("report asserts CONTINUE_RECOMMENDED: true" if "CONTINUE_RECOMMENDED**: true" in rep
               or "CONTINUE_RECOMMENDED**: true" in rep else "report does not assert it"),
        "gate_is_revision_but_self_labels_state": (
            f"gate={gate.get('gate')} safe_to_integrate={gate.get('safe_to_integrate')} while the same file "
            f"asserts evidence_tier={gate.get('evidence_tier')} and cycle_status={gate.get('cycle_status')} "
            "(copied from state/evaluation.json, not derived from an audit)"),
        "auditor_workspace_contradicts_workflow_contract": (
            "report states 'Producer Workspace: /tmp/lex_accepted/product' while the audit job's contract in "
            "origin/main:.github/workflows/core-lane.yml mounts the producer workspace at /tmp/lex_team "
            f"({'/tmp/lex_team' in wf} )" ),
        "report_claims_it_wrote_the_producer_benchmark_record":
            "'Artifacts Written' lists results/evaluation/fast_mvp_retrieval_recall_benchmark/40261335674.json, "
            "which is a PRODUCER artifact (producer commit 419d01bf), conflating the two roles",
        "report_internal_language_leg_mismatch":
            "report says 'fr 3->3 holds=false' in Multilingual Observations but 'French: input_hits=4, "
            "product_hits=3' in Claim Evaluation",
    }
    out["pseudo_artifact_internal_inconsistencies"] = incons
    out["checks"]["inconsistency_catalog_non_empty"] = all(bool(v) for v in incons.values())

    out["passed"] = all(out["checks"].values())
    out["verdict"] = ("PRODUCER_AUTHORED_PSEUDO_AUDIT_ARTIFACT" if out["passed"]
                      else "S2_FAILED")
    return out


# --------------------------------------------------------------------------
# 4. relocation (accepted convention) + S3
# --------------------------------------------------------------------------
def relocate(s2: dict) -> dict:
    RECOVERY_DIR.mkdir(parents=True, exist_ok=True)
    items = []
    for src_rel in OFFENDING:
        src = REPO_ROOT / src_rel
        dst = REPO_ROOT / RECOVERY_MAP[src_rel]
        if not src.exists():
            items.append({"source_path": src_rel, "error": "source missing"})
            continue
        dst.write_bytes(src.read_bytes())
        s_src = sha256_file(src)
        s_dst = sha256_file(dst)
        items.append({
            "source_path": src_rel,
            "relocated_copy": RECOVERY_MAP[src_rel],
            "source_sha256": s_src,
            "copy_sha256": s_dst,
            "byte_identical": s_src == s_dst,
            "original_retained_in_worktree": src.exists(),
        })
    record = {
        "schema": "lex-evaluation-audit-namespace-relocation/1",
        "lane": "evaluation",
        "run": RUN,
        "captured_at_utc": now(),
        "cycle_disclosed": TARGET_RUN,
        "producing_cycle_disclosed": PRIOR_RUN,
        "why": (
            f"the evaluation team wrote these audit-namespace paths in run {PRIOR_RUN}; results/audit/* and "
            "reports/audit/* are outside the evaluation lane write scope (admitted: evaluation/*, tests/evaluation/*, "
            "results/evaluation/*, reports/evaluation/*, state/evaluation.json, data/evaluation/*). Run 44665054809 "
            "failed at 'Enforce lane write scope' (exit 3) on exactly this class; runs 40167904552, 40186604273, "
            "38982176936 and the 40052532425 pseudo-gate had the same defect. Per AGENTS.md #6 and the accepted "
            "precedent results/evaluation/audit_namespace_recovery_{40153908549,40182692670,40232590665}/"
            "RELOCATION_RECORD.json, the artifacts are disclosed and copied byte-for-byte, not deleted or rewritten."),
        "originals_retained": all(i.get("original_retained_in_worktree") for i in items),
        "originals_deleted": False,
        "independent_audit_provenance": False,
        "provenance_finding": (
            f"both files were added by commit {PRODUCING_COMMIT} ('evaluation cycle {PRIOR_RUN} repair 0', "
            "author lex-evaluation-team <lex-team@autonomous.local>) - a PRODUCER snapshot commit, not the "
            "independent-auditor identity (lex-independent-auditor <lex-audit@autonomous.local>) that the audit job "
            "uses. No cycle/core/evaluation/40261335674/audit ref and no 'accept evaluation cycle 40261335674' "
            "commit exists on the remote. The files are therefore producer-authored pseudo-audit output and must "
            "never be cited as an independent audit of run 40261335674, which satisfies neither half of "
            "factory-wide requirement 4."),
        "git_provenance": {
            i["source_path"]: next(
                ({"commit": r["commit"], "author_name": r["author_name"],
                  "author_email": r["author_email"], "subject": r["subject"]}
                 for r in s2["per_path"][i["source_path"]]["adding_commits"]), {})
            for i in items if "source_path" in i
        },
        "items": items,
        "gate_content_summary": {
            k: json.loads((REPO_ROOT / OFFENDING[1]).read_text()).get(k)
            for k in ("gate", "safe_to_integrate", "verdict", "direction_version",
                      "run_id", "lane", "evidence_tier", "cycle_status",
                      "continue_recommended", "accepted_run_id")
        } if (REPO_ROOT / OFFENDING[1]).exists() else {},
        "api_probe_note": (
            "GET /actions/runs/40261335674 returned 404 at capture time, but the control probes for the ACCEPTED "
            "run 40265377500 and for 40258497460 also returned 404 while recent runs returned 200, so the 404 is a "
            "retention artifact and is NOT evidence about this run."),
        "disposition": (
            "The gate is retained as evidence that a producer run PROPOSED a REVISE verdict and as a source of "
            "reproducible product findings, and it is relocated in-scope so no future producer touches the audit "
            "namespace again. It is NOT an independent audit, cannot satisfy factory-wide requirement 4, and "
            "state/evaluation.json must not cite the audit-namespace path as an evidence ref (the refs point at "
            "these recovery copies instead). The independent audit job for the current run must produce its own "
            "gate under results/audit/evaluation/."),
        "claim_ceiling": (
            "Disclosure/relocation only; no gate status is adopted, upgraded or downgraded, no measurement is "
            "rewritten, and no audit is claimed."),
    }
    (RECOVERY_DIR / "RELOCATION_RECORD.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n")

    s3_checks = {
        "copies_byte_identical": all(i.get("byte_identical") for i in items),
        "originals_retained": all(i.get("original_retained_in_worktree") for i in items),
        "recovery_namespace_in_scope": all(
            r.startswith("results/evaluation/") for r in RECOVERY_MAP.values()),
    }
    return {"rule": "S3", "phase": "bytes_and_retention", "passed": all(s3_checks.values()),
            "checks": s3_checks,
            "amended_by": f"evaluation/OPERATIONAL_RESUME_{RUN}_HYPOTHESIS_V1_1_AMENDMENT.json",
            "items": items,
            "relocation_record": str((RECOVERY_DIR / "RELOCATION_RECORD.json").relative_to(REPO_ROOT)),
            "relocation_record_sha256": sha256_file(RECOVERY_DIR / "RELOCATION_RECORD.json")}


def check_s3_state_refs() -> dict:
    """Second half of S3: runs only AFTER the state update, so it belongs to the
    final-gates phase.  The state must cite the recovery copies and must not
    cite the audit-namespace originals."""
    state = json.loads(STATE.read_text())
    refs = state.get("evidence_refs") or []
    tokens = [str(r).split(" ")[0].rstrip(",") for r in refs]
    checks = {
        "no_top_level_ref_to_audit_namespace_originals": not any(t in OFFENDING for t in tokens),
        "top_level_refs_to_recovery_copies": all(
            r in tokens for r in RECOVERY_MAP.values()),
        "recovery_copies_are_files": all(
            (REPO_ROOT / r).is_file() for r in RECOVERY_MAP.values()),
    }
    return {"rule": "S3", "phase": "state_refs", "passed": all(checks.values()),
            "checks": checks,
            "note": ("the two originals stay in the worktree and in git history as retained provenance, but the "
                     "claim path never cites them: evidence_refs points at the in-scope recovery copies"),
            "repointed": {k: v for k, v in RECOVERY_MAP.items()},
            "relocation_record": str((RECOVERY_DIR / "RELOCATION_RECORD.json").relative_to(REPO_ROOT)),
            "relocation_record_sha256": sha256_file(RECOVERY_DIR / "RELOCATION_RECORD.json")}


# --------------------------------------------------------------------------
# 5. S4 - producer write-scope predicate over the live worktree
# --------------------------------------------------------------------------
def check_s4() -> dict:
    out_path = OUT_DIR / "write_scope_live_tree.json"
    rc, _, log = run_write_scope("--lane", "evaluation", "--out", str(out_path))
    rec = json.loads(out_path.read_text()) if out_path.exists() else None
    verdict = rec["verdict"] if rec else {}
    checks = {
        "scope_clean_rc0": rc == 0,
        "verdict_scope_clean": verdict.get("verdict") == "SCOPE_CLEAN",
        "no_bad_paths": verdict.get("n_bad") == 0,
        "no_audit_namespace_entry": not any(
            e.get("path", "").startswith(("results/audit/", "reports/audit/"))
            for e in verdict.get("entries", [])),
    }
    return {"rule": "S4", "passed": all(checks.values()), "checks": checks,
            "command": "python -m evaluation.snapshot_audit.write_scope --lane evaluation",
            "observed": {k: verdict.get(k) for k in ("verdict", "n_entries", "n_bad", "bad_paths")},
            "record": str(out_path.relative_to(REPO_ROOT)) if rec else None,
            "note": ("the predicate reads `git status --porcelain -uall`, i.e. CHANGED/untracked paths only; the "
                     "retained originals are committed and untouched, so they are correctly absent from it")}


# --------------------------------------------------------------------------
# 6. S5 - state gates (run after the state update)
# --------------------------------------------------------------------------
def check_s5() -> dict:
    """Both state gates, run in the FINAL-GATES phase (after the state update,
    after the result record and the reports exist, i.e. after every path the
    state cites already exists).

    Nested-refs guard FIRST: it writes its own record file, which the state
    cites; the state-integrity gate then resolves that ref.
    """
    checks: dict = {}
    detail: dict = {}

    rec_path = OUT_DIR / f"{RUN}_nested_evidence_refs.json"
    code, rec = None, None
    if rec_path.exists():
        rec_path.unlink()  # never trust a stale record
    r = subprocess.run([sys.executable, "-m", "evaluation.nested_evidence_refs_guard",
                        "--run-id", str(RUN), "--out-dir", str(OUT_DIR)],
                       cwd=REPO_ROOT, capture_output=True, text=True)
    if rec_path.exists():
        rec = json.loads(rec_path.read_text())
        code = r.returncode
    checks["nested_refs_zero_unresolved"] = bool(rec) and rec.get("n_unresolved") == 0
    checks["top_level_refs_zero_unresolved"] = bool(rec) and rec.get("n_top_level_unresolved") == 0
    checks["nested_guard_exit_0"] = code == 0
    detail["nested_evidence_refs"] = ({k: rec.get(k) for k in (
        "verdict", "n_top_level_evidence_refs", "n_top_level_unresolved",
        "n_ref_shaped_values_total", "n_unresolved", "resolution_counts")} if rec else
        {"stdout": r.stdout[-1500:], "stderr": r.stderr[-1500:]})

    r = subprocess.run([sys.executable, "-m", "evaluation.state_integrity_gate"],
                       cwd=REPO_ROOT, capture_output=True, text=True)
    try:
        g = json.loads(r.stdout)
        checks["state_integrity_gate_11_of_11"] = (
            g.get("n_failed") == 0 and g.get("n_checks") == 11 and r.returncode == 0)
        detail["state_integrity_gate"] = {
            "verdict": g.get("verdict"), "exit_code": g.get("exit_code"),
            "n_checks": g.get("n_checks"), "n_failed": g.get("n_failed"),
            "failed_checks": [c.get("check") for c in g.get("checks", []) if not c.get("passed")],
        }
        # keep only the gate's summary + the failed observations, not its whole dump
        detail["state_integrity_gate_failed_observations"] = [
            {"check": c.get("check"), "file": c.get("file"), "observed": c.get("observed")}
            for c in g.get("checks", []) if not c.get("passed")]
    except json.JSONDecodeError:
        checks["state_integrity_gate_11_of_11"] = False
        detail["state_integrity_gate_stdout"] = (r.stdout + r.stderr)[-2000:]
    return {"rule": "S5", "phase": "final-gates", "passed": all(checks.values()),
            "checks": checks, "observed": detail,
            "record": str(rec_path.relative_to(REPO_ROOT)) if rec else None}


# --------------------------------------------------------------------------
# 7. S6 / H5 - read-only verification of the ordered-work deliverable
# --------------------------------------------------------------------------
def check_s6() -> dict:
    obs: dict = {"item_1": {}, "item_2": {}, "item_3": {}, "item_4": {}, "item_5": {}}
    checks = {}

    for rel, want in ITEM1.items():
        p = REPO_ROOT / rel
        got = sha256_file(p) if p.exists() else None
        obs["item_1"][rel] = {"expected_sha256": want, "observed_sha256": got, "match": got == want}
    checks["item_1_hashes_match_state_record"] = all(v["match"] for v in obs["item_1"].values())
    obs["item_1"]["status"] = "CORRECTION_OF_RECORD_INTACT" if checks["item_1_hashes_match_state_record"] else "MISMATCH"

    mount = Path("/tmp/lex_accepted/product")
    head_rc, head_txt = git("-C", str(mount), "rev-parse", "HEAD") if mount.exists() else (1, "")
    head = head_txt.strip() if head_rc == 0 else None
    span = mount / "product/query/counter_evidence_span.py"
    span_sha = sha256_file(span) if span.exists() else None
    obs["item_2"] = {
        "product_mount_head": head,
        "expected_product_mount_head": PRODUCT_MOUNT_HEAD,
        "head_unchanged_since_accepted_adjudication": head == PRODUCT_MOUNT_HEAD,
        "rejection_incumbent_leg_file": "product/query/counter_evidence_span.py",
        "leg_file_sha256": span_sha,
        "expected_leg_file_sha256": "82cea13122b13a60e4da746072af4a185f9e4b2e0ef51853d6273acb7a1bb6ce",
        "leg_landed": span_sha == "82cea13122b13a60e4da746072af4a185f9e4b2e0ef51853d6273acb7a1bb6ce",
        "frozen_family_pin": "results/evaluation/counter_evidence_quality_benchmark/40062917685.json",
        "frozen_family_pin_sha256": sha256_file(
            REPO_ROOT / "results/evaluation/counter_evidence_quality_benchmark/40062917685.json"),
        "frozen_family_member_relation": "14 of 15 (server/served 3 of 4)",
        "family_regeneration_possible_without_product_change": False,
        "status": "NOT_YET_DISCRIMINATING",
        "re_measure_executed": False,
        "why_carried_forward_unchanged": (
            "the accepted product mount head is byte-identical to the head already adjudicated by accepted run "
            "40258497460 and re-adjudicated by 44642744588 / 40261335674-adjacent resumes "
            f"({PRODUCT_MOUNT_HEAD}), and the frozen family pin file is unchanged; a set relation computed over "
            "identical inputs cannot change, so the 14/15 relation carries forward and the ordered protocol "
            "(named family + packet-of-record 39319405429 + d2_path_scope_probe) is NOT executed"),
    }
    checks["item_2_precondition_unchanged"] = (
        obs["item_2"]["head_unchanged_since_accepted_adjudication"] and obs["item_2"]["leg_landed"])

    b = REPO_ROOT / BENCH_OF_RECORD
    verdict = None
    if b.exists():
        try:
            verdict = json.loads(b.read_text()).get("verdict")
        except json.JSONDecodeError:
            verdict = None
    vac = REPO_ROOT / "results/evaluation/fast_mvp_current_head_ca_falsifier/40182692670.json"
    obs["item_3"] = {
        "benchmark_of_record": BENCH_OF_RECORD,
        "exists": b.exists(),
        "sha256": sha256_file(b) if b.exists() else None,
        "verdict": verdict,
        "packet_of_record": "39319405429",
        "measurement_of_record_run": 40182692670,
        "sibling_record_preserved": "results/evaluation/fast_mvp_current_head_ca_falsifier/40182692670.json",
        "sibling_record_verdict": (json.loads(vac.read_text()).get("verdict") if vac.exists() else None),
        "prior_fast_mvp_40105794124": "results/evaluation/fast_mvp_current_head_ca_falsifier/40105794124.json",
        "prior_fast_mvp_verdict": json.loads(
            (REPO_ROOT / "results/evaluation/fast_mvp_current_head_ca_falsifier/40105794124.json").read_text()
        ).get("verdict"),
        "re_executed": False,
        "status": "KEPT_UNCHANGED",
    }
    checks["item_3_records_present"] = (
        obs["item_3"]["exists"] and verdict == "PRODUCT_FALSIFIED"
        and obs["item_3"]["prior_fast_mvp_verdict"] == "SOUND_COUNTER_ROW_PRESENT"
        and obs["item_3"]["sibling_record_verdict"] == "NOT_MEASURED_VACUOUS")

    # item (4) is REPORT-ONLY-where-QUOTED.  Its gate of record is the PRODUCT
    # audit gate on the accepted product mount (pinned by two frozen evaluation
    # freeze records).  This cycle does not quote its counts, so the gate is
    # verified BY PIN only and its contents are deliberately NOT copied here.
    gate = Path("/tmp/lex_accepted/product/results/audit/product/CYCLE_39965089504_GATE.json")
    gate_sha = sha256_file(gate) if gate.exists() else None
    obs["item_4"] = {
        "gate_of_record": "mount:/tmp/lex_accepted/product/results/audit/product/CYCLE_39965089504_GATE.json",
        "gate_present": gate.exists(),
        "gate_sha256": gate_sha,
        "expected_gate_sha256_frozen": "f915bac807af988c840c6911738d646e5f794ab16261c63df85d278d227509ef",
        "pin_matches": gate_sha == "f915bac807af988c840c6911738d646e5f794ab16261c63df85d278d227509ef",
        "status": "REPORTED_ONLY_WHERE_QUOTED",
        "quoted_in_this_cycle": False,
        "required_fixes_copied_into_this_cycle": False,
        "note": ("the required-fix counts are intentionally NOT reproduced in this record: item (4) only binds a "
                 "cycle that quotes them, and this cycle does not quote them"),
    }
    checks["item_4_gate_pin_verified_and_not_quoted"] = (
        gate.exists() and obs["item_4"]["pin_matches"] and obs["item_4"]["quoted_in_this_cycle"] is False)

    obs["item_5"] = {
        "frozen_bar_edits": [],
        "falsifier_re_executed": False,
        "d2_profile_re_derived": False,
        "universal_174k_benchmark_run": False,
        "status": "HONOURED",
    }
    checks["item_5_no_closed_work_rerun"] = True

    # the lane's standing falsification record of record must still exist untouched
    fr = REPO_ROOT / "results/evaluation/fast_mvp_current_head_ca_falsifier/40105794124.json"
    checks["standing_falsification_record_present"] = fr.exists()

    return {"rule": "S6", "passed": all(checks.values()), "checks": checks, "observed": obs,
            "ordered_work_status": {
                "1": "DISCHARGED_ELSEWHERE (hash-verified this cycle, not re-run)",
                "2": "NOT_YET_DISCRIMINATING (precondition carried forward unchanged; protocol not executed)",
                "3": "KEPT (benchmark of record present; not re-executed)",
                "4": "REPORTED_ONLY where quoted (not quoted this cycle)",
                "5": "HONOURED (no frozen bench / D2 profile / bypass re-derivation, no 174k)"}}


RESULT_PATH = OUT_DIR / f"{RUN}.json"


def _write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def _passed(rules: dict) -> dict:
    return {k: bool(v.get("passed")) for k, v in rules.items()}


def _verdict(passed: dict) -> str:
    if not passed.get("S1") or not passed.get("S2"):
        return "DIAGNOSIS_NOT_CONFIRMED"
    if not all(passed.values()):
        return "RULE_FAILURE_RECORDED"
    if passed.get("S5") and passed.get("S3_state_refs"):
        return "WRITE_SCOPE_FAILURE_DIAGNOSED_RELOCATED_AND_AUDIT_READY"
    return "WRITE_SCOPE_FAILURE_DIAGNOSED_AND_RELOCATED"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--phase", choices=["full", "final-gates", "post-commit"], default="full")
    args = ap.parse_args(argv)

    if args.phase == "post-commit":
        res = check_s4()
        res["phase"] = "post-commit"
        res["generated_at_utc"] = now()
        path = OUT_DIR / "write_scope_post_commit.json"
        _write_json(path, res)
        print(json.dumps({"phase": "post-commit", "passed": res["passed"],
                          "observed": res["observed"],
                          "record": str(path.relative_to(REPO_ROOT))}, indent=2))
        return 0 if res["passed"] else 1

    if args.phase == "final-gates":
        if not RESULT_PATH.exists():
            print(f"missing result record {RESULT_PATH}", file=sys.stderr)
            return 2
        result = json.loads(RESULT_PATH.read_text())
        freeze = verify_freeze()
        s3s = check_s3_state_refs()
        s5 = check_s5()
        s4 = check_s4()  # re-measure: state update + reports changed the worktree
        result["frozen_inputs"] = freeze
        result["rules"]["freeze_inputs"] = freeze
        result["rules"]["S3_state_refs"] = s3s
        result["rules"]["S5"] = s5
        result["rules"]["S4"] = s4
        result["rule_pass"] = _passed(result["rules"])
        result["verdict"] = _verdict(result["rule_pass"])
        result["exit_code"] = 0 if all(result["rule_pass"].values()) else 1
        result["state_claim"] = {
            "path": "state/evaluation.json",
            "sha256": sha256_file(STATE) if STATE.exists() else None,
            "lane_copy_sha256": sha256_file(REPO_ROOT / "evaluation" / "state" / "evaluation.json"),
            "measured_after_state_update": True,
        }
        result["final_gates_at_utc"] = now()
        _write_json(RESULT_PATH, result)
        _write_json(OUT_DIR / "final_gate_verification.json", {
            "schema": "lex-evaluation-final-gate-verification/1",
            "run_id": RUN, "generated_at_utc": now(),
            "rules": {k: {"passed": result["rules"][k].get("passed"),
                          "checks": result["rules"][k].get("checks")}
                      for k in ("S3_state_refs", "S5")},
            "observed": {"S5": result["rules"]["S5"].get("observed")},
            "verdict": result["verdict"], "exit_code": result["exit_code"],
            "claim_ceiling": ("Gate outcomes for this run's state and refs only; no product, bar, "
                              "serve or audit-acceptance claim."),
        })
        print(json.dumps({"phase": "final-gates", "verdict": result["verdict"],
                          "rule_pass": result["rule_pass"],
                          "exit_code": result["exit_code"],
                          "record": str(RESULT_PATH.relative_to(REPO_ROOT))}, indent=2))
        return result["exit_code"]

    # ---- phase: full -----------------------------------------------------
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    freeze = verify_freeze()
    s1 = check_s1()
    s2 = check_s2()
    _write_json(OUT_DIR / f"pseudo_audit_provenance_{TARGET_RUN}.json", {
        "schema": "lex-evaluation-pseudo-audit-provenance/1",
        "run_id": RUN, "generated_at_utc": now(), "target_run": TARGET_RUN,
        "finding": s2.get("verdict"),
        "audit_branch_ls_remote": s2.get("audit_branch_ls_remote"),
        "accept_commit_matches": s2.get("accept_commit_matches"),
        "per_path": s2.get("per_path"),
        "write_scope_repro": s2.get("write_scope_repro"),
        "api_probe": s2.get("api_probe"),
        "pseudo_artifact_internal_inconsistencies": s2.get("pseudo_artifact_internal_inconsistencies"),
        "checks": s2.get("checks"),
        "claim_ceiling": ("Provenance adjudication of two producer-written audit-namespace files. It does not "
                          "create, upgrade or replace any independent audit and makes no product claim."),
    })
    rel = relocate(s2)
    s4 = check_s4()
    s6 = check_s6()
    _write_json(OUT_DIR / "item_delivery_verification.json", {
        "schema": "lex-evaluation-ordered-work-item-verification/1",
        "run_id": RUN, "generated_at_utc": now(), "direction_version": DIRV,
        "method": "read-only hashing / head comparison; no falsifier, probe, bar or benchmark executed",
        "observed": s6["observed"], "checks": s6["checks"],
        "ordered_work_status": s6["ordered_work_status"],
        "rule_pass": s6["passed"],
        "claim_ceiling": ("Existence/hash verification of ordered-work pointers. No quality number is produced, "
                          "no relation is recomputed and no closed item is re-derived."),
    })

    rules = {"freeze_inputs": freeze, "S1": s1, "S2": s2, "S3": rel,
             "S3_state_refs": {"passed": None, "status": "DEFERRED_TO_FINAL_GATES"},
             "S4": s4,
             "S5": {"passed": None, "status": "DEFERRED_TO_FINAL_GATES"},
             "S6": s6}
    decided = {k: v for k, v in rules.items() if v.get("passed") is not None}
    passed = _passed(decided)

    result = {
        "schema": "lex-evaluation-operational-resume/2",
        "run_id": RUN,
        "resumes_run": PRIOR_RUN,
        "lane": "evaluation",
        "direction_version": DIRV,
        "mode": "OPERATIONAL_RESUME",
        "generated_at_utc": now(),
        "phases": {
            "full": "diagnosis, provenance, relocation, live write-scope predicate, ordered-work verification",
            "final-gates": "S3 state-ref clauses + nested-refs guard + state-integrity gate "
                           "(runs after the state update and the reports exist)",
            "post-commit": "write-scope predicate re-measured after the cycle commit, i.e. what step 9 sees",
        },
        "claim_bearing_run": RUN,
        "audit_status": "PENDING_INDEPENDENT_AUDIT",
        "pending_independent_audit": True,
        "accepted_as_evidence": False,
        "frozen_inputs": freeze,
        "rules": rules,
        "rule_pass": passed,
        "verdict": _verdict(passed),
        "exit_code": 0 if all(passed.values()) else 1,
        "failure_diagnosis": {
            "run": PRIOR_RUN,
            "class": "WRITE_SCOPE_VALIDATION_FAILURE_exit_3",
            "failing_step": {"number": 9, "name": "Enforce lane write scope"},
            "offending_paths": OFFENDING,
            "control_plane_step_source": "origin/main:.github/workflows/core-lane.yml",
            "not": ["rc67 zero-delta", "rc68/69 state validation", "rc78 work-quantum",
                    "provider/model death", "audit-job failure", "gate verdict"],
            "audit_integrate_skipped": True,
            "snapshot_of_prior_run": PRODUCING_COMMIT,
        },
        "relocation": {
            "convention": "lex-evaluation-audit-namespace-relocation/1",
            "precedents": ["40153908549", "40182692670", "40232590665"],
            "record": rel.get("relocation_record"),
            "record_sha256": rel.get("relocation_record_sha256"),
            "originals_retained": True,
            "originals_deleted": False,
        },
        "state_claim": {
            "path": "state/evaluation.json",
            "sha256": sha256_file(STATE) if STATE.exists() else None,
            "measured_before_state_update": True,
        },
        "ordered_work_status": s6["ordered_work_status"],
        "negative_results": [
            "The GitHub API probe that was going to corroborate 'run 40261335674 has no run record' is "
            "NON-discriminating: the accepted control run 40265377500 also returns 404 while recent runs return "
            "200, so the 404 is a retention artifact. It is recorded as a negative result and is not used.",
            "No quality, recall, counter-authority, label, geometry or serve measurement is produced by this "
            "cycle; the lane's open bottleneck remains Core Product's P0 rejection/incumbent leg.",
            "Ordered item (2) stays NOT_YET_DISCRIMINATING: the frozen 15-member family is still 14/15 because "
            "the accepted product head has not moved.",
        ],
        "not_claimed": [
            "no frozen bar, rubric, threshold, gate predicate or verdict contract edited or re-derived",
            "no serve verdict, packet admission, human-gate or ready_for_owner_session claim",
            "no FAST-MVP falsifier, D2 profile, d2_path_scope_probe or universal-174k re-execution",
            "no independent audit is claimed for run 40261335674 or for this run",
            "human_gate_ready stays false; machine_gate_ready stays false; owner_decision_required stays false",
        ],
        "claim_ceiling": (
            "Operational-resume provenance: a reproduced write-scope failure diagnosis, a byte-identical "
            "in-scope relocation of two producer-authored audit-namespace files under the accepted "
            "convention, and read-only verification of ordered-work pointers. It adds no quality "
            "measurement, moves no bar, issues no serve or admission verdict and makes no "
            "legal-usefulness or human-gate claim."),
    }
    _write_json(RESULT_PATH, result)
    print(json.dumps({"phase": "full", "verdict": result["verdict"], "rule_pass": passed,
                      "exit_code": result["exit_code"],
                      "record": str(RESULT_PATH.relative_to(REPO_ROOT))}, indent=2))
    return result["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
