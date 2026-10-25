#!/usr/bin/env python3
"""Operational-resume verifier and compact audit pack for evaluation run 40204378896.

Base: the persisted producer snapshot of run 40198184759 (commit 251a6f59).
This resume does NOT start over and does NOT re-score any benchmark:

  * it diagnoses the orchestration failure of run 40198184759 from the public
    GitHub run/jobs JSON and the checked-in work-quantum wrapper;
  * it proves that the prior audit-ready pack is preserved byte-for-byte
    against the snapshot commit;
  * it re-executes the prior deliverable verifier against the current accepted
    Product mount (when that mount is available) and preserves the result;
  * it reads the lane's own state/scope/test instruments and builds one
    compact, hash-indexed audit pack.

Claim ceiling: operational-resume verification only. No frozen bar, rubric,
threshold, serve verdict, admission flag or new same-question cycle is touched.

Usage (from the producer/team worktree):
    python3 evaluation/operational_resume_40204378896.py prepare
    python3 evaluation/operational_resume_40204378896.py finalize

`prepare` writes diagnosis/snapshot/deliverable-replay records.
`finalize` is run after the state and instrument records are final; it writes
the summary and the hash-indexed audit pack.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

RUN_ID = "40204378896"
RESUMED_RUN_ID = "40198184759"
PRIOR_RUNS = ("40192868113", "40187594111")
PRIOR_SNAPSHOT = "251a6f5967c653d3ca93bf0a2d3ad7a1dd3f875e"
PRIOR_PRIOR_SNAPSHOT = "ef0285cc175c9f337463945f3a0c2eefa02afd86"
PRIOR_ACCEPTED_RUN = 40159747851
PRIOR_ACCEPT_COMMIT = "9be8a7d5b3a4b84eb45da6160bf90620f7d81d40"
ACCEPTED_BASE_COMMIT = "9be8a7d5b3a4b84eb45da6160bf90620f7d81d40"
GENERATED_AT_UTC = "2026-10-25T14:53:49Z"  # run 40204378896 creation time
REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "results/evaluation/operational_resume_40204378896"
PRODUCT_MOUNT = Path("/tmp/lex_accepted/product")
OLD_PACK = REPO / "results/evaluation/operational_resume_40198184759"
OLD_MANIFEST = REPO / "results/evaluation/operational_resume_40192868113/manifest_40192868113.json"
HYPOTHESIS = REPO / "evaluation/OPERATIONAL_RESUME_40204378896_HYPOTHESIS_V1.json"
FREEZE = REPO / "evaluation/OPERATIONAL_RESUME_40204378896_FREEZE_V1.json"
REPORT = REPO / "reports/evaluation/OPERATIONAL_RESUME_40204378896_AUDIT_READY.md"
FROZEN_LABEL_SHA = "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"
FROZEN_GEOMETRY_SHA = "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, indent=2, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")
    return sha256_bytes(text.encode())


def git(*args: str, cwd: Path = REPO) -> tuple[int, str, str]:
    p = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def git_bytes(*args: str, cwd: Path = REPO) -> tuple[int, bytes, bytes]:
    """Return raw bytes: `git show` through the text helper would strip the
    trailing newline and silently corrupt every content hash."""
    p = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True)
    return p.returncode, p.stdout, p.stderr


def parse_ts(s):
    if not s:
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def seconds_between(a, b):
    x, y = parse_ts(a), parse_ts(b)
    if not x or not y:
        return None
    return round((y - x).total_seconds(), 1)


def check(name: str, ok: bool, **detail) -> dict:
    return {"check": name, "ok": bool(ok), **detail}


def api_jobs(path: Path) -> dict:
    return load_json(path)


def job_by_name(jobs: dict, name: str) -> dict:
    return next((j for j in jobs.get("jobs") or [] if j.get("name") == name), {})


def failing_step(job: dict) -> dict:
    return next((s for s in job.get("steps") or [] if s.get("conclusion") == "failure"), {})


def audit_branch_probe(run_id: str) -> dict:
    rc, out, err = git("ls-remote", "--heads", "origin", f"refs/heads/cycle/core/evaluation/{run_id}/*")
    refs = [line.split("\t")[-1] for line in out.splitlines() if line.strip()]
    audit_refs = [r for r in refs if r.endswith("/audit")]
    return {"command": f"git ls-remote --heads origin refs/heads/cycle/core/evaluation/{run_id}/*",
            "returncode": rc, "refs": refs, "audit_refs": audit_refs,
            "audit_branch_present": bool(audit_refs), "stderr": err}


def wrapper_quantum() -> dict:
    rc, wrapper, err = git("show", "origin/main:.github/scripts/run-ox-with-retry.sh")
    m = re.search(r'WORK_QUANTUM_SECONDS="\$\{LEX_AGENT_QUANTUM_SECONDS:-(\d+)\}"', wrapper or "")
    lines = (wrapper or "").splitlines()
    def line_of(needle):
        return next((i + 1 for i, line in enumerate(lines) if needle in line), None)
    return {
        "source": "origin/main:.github/scripts/run-ox-with-retry.sh",
        "seconds": int(m.group(1)) if m else None,
        "quantum_line": line_of("WORK_QUANTUM_SECONDS="),
        "warning_line": line_of("LEX_WORK_QUANTUM_EXPIRED"),
        "exit78_line": next((i + 1 for i, line in enumerate(lines) if line.strip() == "exit 78"), None),
        "warning_text": "::warning::LEX_WORK_QUANTUM_EXPIRED seconds=<quantum> pid=<child>",
        "exit_code": 78,
        "git_show_returncode": rc,
        "stderr": err,
    }


def build_diagnosis() -> dict:
    run = load_json(OUT / "run_40198184759_api.json")
    jobs = api_jobs(OUT / "jobs_40198184759_api.json")
    team = job_by_name(jobs, "team")
    audit = job_by_name(jobs, "audit")
    integrate = job_by_name(jobs, "integrate")
    resilience = job_by_name(jobs, "resilience")
    fail = failing_step(audit)
    skipped = [s.get("name") for s in audit.get("steps") or [] if s.get("conclusion") == "skipped"]
    audit_seconds = seconds_between(audit.get("started_at"), audit.get("completed_at"))
    step_seconds = seconds_between(fail.get("started_at"), fail.get("completed_at"))
    q = wrapper_quantum()
    branch = audit_branch_probe(RESUMED_RUN_ID)
    team_steps = {s.get("name"): s.get("conclusion") for s in team.get("steps") or []}

    prior = []
    for rid in PRIOR_RUNS:
        p = OLD_PACK / f"jobs_{rid}_final.json"
        if p.is_file():
            j = api_jobs(p)
            a = job_by_name(j, "audit")
            f = failing_step(a)
            prior.append({"run_id": rid,
                          "audit_conclusion": a.get("conclusion"),
                          "failing_step": f.get("name"),
                          "failing_step_seconds": seconds_between(f.get("started_at"), f.get("completed_at")),
                          "audit_seconds": seconds_between(a.get("started_at"), a.get("completed_at"))})
    same_signature = all(x.get("failing_step") == "Independent audit"
                         and x.get("failing_step_seconds") is not None
                         and abs(x["failing_step_seconds"] - (q.get("seconds") or 0)) <= 10
                         for x in prior)
    quantum_match = (q.get("seconds") is not None and step_seconds is not None
                     and abs(step_seconds - q["seconds"]) <= 10)

    checks = [
        check("team_job_success", team.get("conclusion") == "success",
              started_at=team.get("started_at"), completed_at=team.get("completed_at")),
        check("all_producer_steps_success",
              all(v == "success" for k, v in team_steps.items()
                  if k in {"Validate lane and initialize working base", "Mount accepted peer evidence",
                           "Run lane cycle", "Validate active MVP producer state",
                           "Clean generated junk", "Enforce lane write scope", "Persist team snapshot"}),
              steps=team_steps),
        check("audit_job_failure", audit.get("conclusion") == "failure",
              started_at=audit.get("started_at"), completed_at=audit.get("completed_at"), seconds=audit_seconds),
        check("failing_step_is_independent_audit", fail.get("name") == "Independent audit",
              failing_step=fail, step_seconds=step_seconds),
        check("audit_quantum_expired",
              quantum_match, audit_step_seconds=step_seconds, wrapper_quantum_seconds=q.get("seconds"),
              delta_seconds=(round(step_seconds - q["seconds"], 1) if step_seconds is not None and q.get("seconds") else None)),
        check("gate_and_snapshot_steps_skipped",
              {"Enforce audit scope and read gate", "Persist audit snapshot"} <= set(skipped), skipped_steps=skipped),
        check("integrate_skipped", integrate.get("conclusion") == "skipped"),
        check("resilience_success", resilience.get("conclusion") == "success"),
        check("no_audit_branch_or_gate", branch.get("returncode") == 0 and not branch.get("audit_branch_present"),
              refs=branch.get("refs")),
        check("recurrence_on_prior_two_runs", same_signature, prior=prior),
        check("producer_snapshot_commit_is_resume_base",
              run.get("head_sha") != PRIOR_SNAPSHOT  # run head is main-at-dispatch; snapshot is team output
              and git("cat-file", "-e", PRIOR_SNAPSHOT + "^{commit}")[0] == 0,
              run_head_sha=run.get("head_sha"), snapshot_commit=PRIOR_SNAPSHOT),
    ]
    return {
        "schema": "lex-evaluation-operational-resume-diagnosis/2",
        "lane": "evaluation",
        "run_id": RUN_ID,
        "resumed_run_id": RESUMED_RUN_ID,
        "generated_at_utc": GENERATED_AT_UTC,
        "classification": "ORCHESTRATION_WORK_QUANTUM_EXPIRED",
        "classification_confidence": "high_on_mechanism_not_proven_on_log_text",
        "why_not_proven": "GitHub job logs require admin rights (HTTP 403 unauthenticated); the 2700s wrapper quantum and the repeatedly identical 2704s audit-step duration are strong but not log-quoted. Nothing in the producer jobs failed.",
        "run": {k: run.get(k) for k in ("head_sha", "event", "created_at", "updated_at", "conclusion", "html_url", "run_attempt", "head_branch")},
        "jobs": {
            "team": {"conclusion": team.get("conclusion"), "started_at": team.get("started_at"),
                     "completed_at": team.get("completed_at"), "steps": team_steps},
            "audit": {"conclusion": audit.get("conclusion"), "started_at": audit.get("started_at"),
                      "completed_at": audit.get("completed_at"), "seconds": audit_seconds,
                      "failing_step": fail, "step_seconds": step_seconds,
                      "skipped_steps": skipped},
            "integrate": {"conclusion": integrate.get("conclusion")},
            "resilience": {"conclusion": resilience.get("conclusion"),
                           "started_at": resilience.get("started_at"),
                           "completed_at": resilience.get("completed_at")},
        },
        "work_quantum": q,
        "audit_branch_probe": branch,
        "recurrence": {"runs": prior, "same_independent_audit_signature": same_signature,
                       "conclusion": "THREE CONSECUTIVE RUNS (40187594111, 40192868113, 40198184759) died in the same independent-audit step at the same quantum boundary and none wrote an audit branch or gate."},
        "checks": checks,
        "all_checks_ok": all(c["ok"] for c in checks),
        "root_cause": "The independent-audit agent is killed by the frozen 2700s work quantum before it writes an audit branch or gate. The producer team job is healthy: all validation, write-scope and snapshot steps succeeded. Integrate correctly skipped; resilience re-dispatched this resume.",
        "not_a_producer_failure": [f"{k}: {v}" for k, v in team_steps.items() if v == "success"],
        "control_plane_note": "This resume does not edit .github/** or the audit quantum. The durable fix is control-plane (smaller/split audit scope or a larger quantum); the lane can only make the snapshot cheaper to audit, which this pack does.",
        "provenance": {
            "run_json": "results/evaluation/operational_resume_40204378896/run_40198184759_api.json",
            "jobs_json": "results/evaluation/operational_resume_40204378896/jobs_40198184759_api.json",
            "api_authentication": False,
            "api_note": "Public GitHub REST API; logs are not available unauthenticated.",
        },
    }


def build_snapshot_integrity() -> dict:
    checks = []
    rc_head, head, _ = git("rev-parse", "HEAD")
    rc_base, _, _ = git("cat-file", "-e", PRIOR_SNAPSHOT + "^{commit}")
    checks.append(check("snapshot_commit_resolvable", rc_base == 0, commit=PRIOR_SNAPSHOT))
    checks.append(check("snapshot_commit_is_ancestor_or_head",
                        rc_head == 0 and (head == PRIOR_SNAPSHOT or git("merge-base", "--is-ancestor", PRIOR_SNAPSHOT, "HEAD")[0] == 0),
                        head=head, snapshot=PRIOR_SNAPSHOT,
                        note="After this resume commit, the snapshot is the parent of HEAD; during the producer run HEAD equals the snapshot."))

    manifest = load_json(OLD_MANIFEST)
    mfiles = manifest.get("files") or []
    state_paths = {"state/evaluation.json", "evaluation/state/evaluation.json"}
    immutable = [r for r in mfiles if r.get("path") not in state_paths]
    mutable_state = [r for r in mfiles if r.get("path") in state_paths]
    bad = []
    for rec in immutable:
        p = REPO / rec["path"]
        if not p.is_file():
            bad.append({"path": rec["path"], "reason": "missing"})
        elif sha256_file(p) != rec.get("sha256"):
            bad.append({"path": rec["path"], "reason": "sha256_mismatch",
                        "expected": rec.get("sha256"), "actual": sha256_file(p)})
    checks.append(check("prior_manifest_immutable_artifacts_preserved",
                        len(immutable) == 20 and not bad, n_manifest=len(mfiles),
                        n_immutable=len(immutable), bad=bad))
    # The two state files are expected to advance (that is what a resume does).
    # Preserve their snapshot versions in git and verify they still carry the
    # same accepted cycle and direction version; never pretend a byte-identical
    # state file is required across a resume.
    state_prev = {}
    for rec in mutable_state:
        # The manifest was produced by run 40192868113, whose snapshot is
        # PRIOR_PRIOR_SNAPSHOT. It is not the 40198184759 snapshot; checking the
        # wrong commit would only prove readability, not that the recorded state
        # bytes are the ones the manifest actually hashed.
        rc, blob, _ = git_bytes("show", f"{PRIOR_PRIOR_SNAPSHOT}:{rec['path']}")
        observed = sha256_bytes(blob) if rc == 0 else None
        state_prev[rec["path"]] = {"snapshot_commit": PRIOR_PRIOR_SNAPSHOT,
                                   "snapshot_sha256": observed,
                                   "snapshot_recorded_sha256": rec.get("sha256"),
                                   "blob_readable": rc == 0,
                                   "matches_manifest": rc == 0 and observed == rec.get("sha256")}
    checks.append(check("prior_state_versions_match_manifest_at_their_snapshot",
                        len(mutable_state) == 2 and all(v["matches_manifest"] for v in state_prev.values()),
                        state_prev=state_prev,
                        note="state files legitimately advance on a resume; their manifest bytes are checked at the run-40192868113 snapshot ef0285cc, not at the later 40198184759 snapshot."))

    # Every file in the prior 40198184759 pack plus its report/followup must be
    # byte-identical to the blob at the snapshot commit. This is the strongest
    # available "no old claim-bearing artifact was rewritten" check.
    rc_ls, ls, err = git("ls-tree", "-r", "--name-only", PRIOR_SNAPSHOT, "--",
                         "results/evaluation/operational_resume_40198184759",
                         "results/evaluation/operational_resume_40192868113",
                         "reports/evaluation/OPERATIONAL_RESUME_40198184759_AUDIT_READY.md",
                         "reports/evaluation/CORRECTION_FOLLOWUP_CITATION_40198184759.md")
    old_paths = [x for x in ls.splitlines() if x.strip()]
    changed = []
    for rel in old_paths:
        rc_show, blob, _ = git_bytes("show", f"{PRIOR_SNAPSHOT}:{rel}")
        if rc_show != 0:
            changed.append({"path": rel, "reason": "blob_unreadable"})
            continue
        p = REPO / rel
        if not p.is_file():
            changed.append({"path": rel, "reason": "missing_worktree"})
        elif sha256_bytes(blob) != sha256_file(p):
            changed.append({"path": rel, "reason": "differs_from_snapshot",
                            "snapshot_sha256": sha256_bytes(blob),
                            "worktree_sha256": sha256_file(p)})
    checks.append(check("old_claim_bearing_artifacts_unchanged", len(old_paths) > 0 and not changed,
                        n_old_paths=len(old_paths), changed=changed, git_stderr=err))

    # State must still point at the same accepted cycle; this resume may not
    # advance acceptance.
    state = load_json(REPO / "state/evaluation.json")
    lane = load_json(REPO / "evaluation/state/evaluation.json")
    checks.append(check("accepted_run_unchanged", state.get("accepted_run_id") == PRIOR_ACCEPTED_RUN
                        and lane.get("accepted_run_id") == PRIOR_ACCEPTED_RUN,
                        root=state.get("accepted_run_id"), lane=lane.get("accepted_run_id")))
    checks.append(check("accepted_accept_commit_still_on_lab_evaluation",
                        git("cat-file", "-e", PRIOR_ACCEPT_COMMIT + "^{commit}")[0] == 0,
                        accept_commit=PRIOR_ACCEPT_COMMIT))
    checks.append(check("frozen_pins_unchanged",
                        sha256_file(REPO / "evaluation/frozen_bars/RULES_LABEL.json") == FROZEN_LABEL_SHA
                        and sha256_file(REPO / "evaluation/frozen_bars/RULES_GEOMETRY.json") == FROZEN_GEOMETRY_SHA,
                        label_sha256=sha256_file(REPO / "evaluation/frozen_bars/RULES_LABEL.json"),
                        geometry_sha256=sha256_file(REPO / "evaluation/frozen_bars/RULES_GEOMETRY.json")))
    checks.append(check("freeze_and_hypothesis_present",
                        HYPOTHESIS.is_file() and FREEZE.is_file()
                        and load_json(FREEZE).get("hypothesis_sha256") == sha256_file(HYPOTHESIS),
                        hypothesis_sha256=sha256_file(HYPOTHESIS) if HYPOTHESIS.is_file() else None,
                        freeze_sha256=sha256_file(FREEZE) if FREEZE.is_file() else None))
    return {
        "schema": "lex-evaluation-operational-resume-snapshot-integrity/1",
        "lane": "evaluation",
        "run_id": RUN_ID,
        "resumed_run_id": RESUMED_RUN_ID,
        "generated_at_utc": GENERATED_AT_UTC,
        "snapshot_commit": PRIOR_SNAPSHOT,
        "prior_snapshot_commit": PRIOR_PRIOR_SNAPSHOT,
        "manifest": str(OLD_MANIFEST.relative_to(REPO)),
        "manifest_sha256": sha256_file(OLD_MANIFEST),
        "checks": checks,
        "all_checks_ok": all(c["ok"] for c in checks),
        "claim_ceiling": "Byte-preservation and pin check only; it does not re-validate the content of the preserved artifacts.",
    }


def ensure_product_objects() -> dict:
    """Make the item-(1) provenance commits resolvable in the Product mount.

    The producer workflow checks out `lab/product` with full history; a bare
    audit checkout may not. The full commit ids are pinned by the prior
    deliverable verification and by factory direction v68. Fetching a commit by
    full id is a provenance repair, not a measurement change.
    """
    commits = {
        "51d306c": "51d306ca4b52c6d8ea1200c306cfb33e44e487ac",
        "85e816f": "85e816fa7e3a5e86671cb813e1c121da64cfd2c7",
        "8b5b08dd": "8b5b08dddeda482961ecfd432a5b5b40675b92ab",
    }
    out = {"mount": str(PRODUCT_MOUNT), "mount_present": PRODUCT_MOUNT.is_dir(),
           "commits": {}, "fetch_attempted": False, "fetch_ok": None, "fetch_stderr": ""}
    if not out["mount_present"]:
        return out
    missing = []
    for short, full in commits.items():
        rc, _, _ = git("cat-file", "-e", full + "^{commit}", cwd=PRODUCT_MOUNT)
        out["commits"][short] = {"full": full, "resolved": rc == 0, "source": "present"}
        if rc != 0:
            missing.append(full)
    if missing:
        out["fetch_attempted"] = True
        rc, stdout, stderr = git("fetch", "--no-tags", "origin", *missing, cwd=PRODUCT_MOUNT)
        out["fetch_ok"] = rc == 0
        out["fetch_stderr"] = stderr[-2000:]
        for short, full in commits.items():
            rc2, _, _ = git("cat-file", "-e", full + "^{commit}", cwd=PRODUCT_MOUNT)
            if rc2 == 0:
                out["commits"][short].update(resolved=True, source="fetched")
    out["all_resolved"] = all(v["resolved"] for v in out["commits"].values())
    return out


def build_deliverable_replay() -> dict:
    """Re-execute the prior resume verifier's 51 deliverable checks.

    This is the same frozen operational-resume instrument, not a new
    falsification. If the accepted Product mount is absent (as in a bare audit
    checkout), fall back to verifying the committed prior record and disclose
    that the mount-dependent checks were not re-executed.
    """
    try:
        sys.path.insert(0, str(REPO))
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "prior_resume_40198184759", REPO / "evaluation/operational_resume_40198184759.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        product_objects = ensure_product_objects()
        mount_ok = PRODUCT_MOUNT.is_dir() and product_objects.get("all_resolved")
        if mount_ok:
            verification = mod.build_deliverable_verification()
            status = "REEXECUTED_AT_CURRENT_MOUNT"
            checks = verification.get("checks") or []
            failed = verification.get("failed_checks") or []
            all_ok = bool(verification.get("all_checks_ok"))
        else:
            prior_record = OLD_PACK / "deliverable_verification_40198184759.json"
            prior = load_json(prior_record)
            checks = [{"check": "accepted_product_mount_available", "ok": False,
                       "path": str(PRODUCT_MOUNT),
                       "why": "The independent-audit checkout does not mount Product peers. Use `git worktree add --detach /tmp/lex_accepted/product origin/lab/product` before this verification if independent recomputation of the item-(1) mount checks is required."}]
            checks += [{"check": f"prior_record::{c.get('check')}", "ok": bool(c.get("ok")),
                        "source": "committed 40198184759 deliverable verification"} for c in prior.get("checks") or []]
            failed = [c["check"] for c in checks if not c["ok"]]
            all_ok = False
            status = "MOUNT_ABSENT_PRIOR_RECORD_VERIFIED_NOT_REEXECUTED"
        source_sha = sha256_file(REPO / "evaluation/operational_resume_40198184759.py")
    except Exception as exc:  # never pretend a replay happened
        checks = [{"check": "prior_instrument_reexecution", "ok": False, "error": repr(exc)}]
        failed = ["prior_instrument_reexecution"]
        all_ok = False
        status = "REEXECUTION_ERROR"
        source_sha = None

    return {
        "schema": "lex-evaluation-operational-resume-deliverable-replay/1",
        "lane": "evaluation",
        "run_id": RUN_ID,
        "resumed_run_id": RESUMED_RUN_ID,
        "generated_at_utc": GENERATED_AT_UTC,
        "source_instrument": "evaluation/operational_resume_40198184759.py",
        "source_instrument_sha256": source_sha,
        "product_object_provenance": product_objects,
        "status": status,
        "n_checks": len(checks),
        "n_checks_ok": sum(1 for c in checks if c.get("ok")),
        "failed_checks": failed,
        "all_checks_ok": all_ok,
        "checks": checks,
        "claim_ceiling": "Replays the prior operational-resume deliverable verification. It preserves the 40105794124 measurement unchanged, keeps item (2) NOT_YET_DISCRIMINATING, and adds no new measurement, bar movement or serve verdict.",
    }


def verify_instrument_records() -> dict:
    """Read the lane's final instrument records and require their pass verdicts."""
    records = {
        "state_integrity_gate": OUT / "state_integrity_gate_40204378896.json",
        "nested_evidence_refs": OUT / "nested_refs/40204378896_nested_evidence_refs.json",
        "pytest_targeted": OUT / "pytest_targeted_40204378896.json",
        "write_scope": OUT / "write_scope_40204378896.json",
    }
    checks = []
    for name, path in records.items():
        if not path.is_file():
            checks.append(check(f"{name}_present", False, path=str(path.relative_to(REPO)), reason="missing"))
            continue
        rec = load_json(path)
        checks.append(check(f"{name}_present", True, path=str(path.relative_to(REPO)), sha256=sha256_file(path)))
        if name == "state_integrity_gate":
            checks.append(check("state_integrity_gate_all_pass",
                                rec.get("verdict") == "ALL_CHECKS_PASS" and rec.get("n_failed") == 0,
                                verdict=rec.get("verdict"), n_passed=rec.get("n_passed"), n_failed=rec.get("n_failed")))
        elif name == "nested_evidence_refs":
            checks.append(check("nested_refs_resolved",
                                rec.get("verdict") == "NESTED_REFS_RESOLVED" and rec.get("n_unresolved") == 0
                                and rec.get("n_top_level_unresolved") == 0,
                                verdict=rec.get("verdict"), n_unresolved=rec.get("n_unresolved"),
                                n_top_level_unresolved=rec.get("n_top_level_unresolved")))
        elif name == "pytest_targeted":
            checks.append(check("targeted_shim_pass",
                                rec.get("verdict") == "SHIM_PASS" and rec.get("n_failed") == 0 and rec.get("n_absent") == 0,
                                verdict=rec.get("verdict"), n_passed=rec.get("n_passed"),
                                n_failed=rec.get("n_failed"), n_unsupported=rec.get("n_unsupported")))
        elif name == "write_scope":
            v = rec.get("verdict") or {}
            checks.append(check("write_scope_clean", v.get("verdict") == "SCOPE_CLEAN" and v.get("n_bad") == 0,
                                verdict=v.get("verdict"), n_bad=v.get("n_bad"), bad_paths=v.get("bad_paths")))
    return {"checks": checks, "all_checks_ok": all(c["ok"] for c in checks)}


def artifact_inventory() -> list[dict]:
    """All artifacts this resume adds, with their current hashes."""
    candidates = [
        "evaluation/OPERATIONAL_RESUME_40204378896_HYPOTHESIS_V1.json",
        "evaluation/OPERATIONAL_RESUME_40204378896_FREEZE_V1.json",
        "evaluation/operational_resume_40204378896.py",
        "results/evaluation/operational_resume_40204378896/run_40198184759_api.json",
        "results/evaluation/operational_resume_40204378896/jobs_40198184759_api.json",
        "results/evaluation/operational_resume_40204378896/provenance_fetch_record_40204378896.json",
        "results/evaluation/operational_resume_40204378896/diagnosis_40198184759.json",
        "results/evaluation/operational_resume_40204378896/snapshot_integrity_40204378896.json",
        "results/evaluation/operational_resume_40204378896/deliverable_verification_replay_40204378896.json",
        "results/evaluation/operational_resume_40204378896/state_integrity_gate_40204378896.json",
        "results/evaluation/operational_resume_40204378896/nested_refs/40204378896_nested_evidence_refs.json",
        "results/evaluation/operational_resume_40204378896/pytest_targeted_40204378896.json",
        "results/evaluation/operational_resume_40204378896/write_scope_40204378896.json",
        "reports/evaluation/OPERATIONAL_RESUME_40204378896_AUDIT_READY.md",
    ]
    inv = []
    for rel in candidates:
        p = REPO / rel
        inv.append({"path": rel, "exists": p.is_file(),
                    "sha256": sha256_file(p) if p.is_file() else None,
                    "bytes": p.stat().st_size if p.is_file() else None})
    return inv


def prepare() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    diag = build_diagnosis()
    diag_sha = write_json(OUT / "diagnosis_40198184759.json", diag)
    snap = build_snapshot_integrity()
    snap_sha = write_json(OUT / "snapshot_integrity_40204378896.json", snap)
    rep = build_deliverable_replay()
    rep_sha = write_json(OUT / "deliverable_verification_replay_40204378896.json", rep)
    out = {
        "diagnosis": {"path": "results/evaluation/operational_resume_40204378896/diagnosis_40198184759.json",
                      "sha256": diag_sha, "classification": diag["classification"], "all_checks_ok": diag["all_checks_ok"]},
        "snapshot_integrity": {"path": "results/evaluation/operational_resume_40204378896/snapshot_integrity_40204378896.json",
                               "sha256": snap_sha, "all_checks_ok": snap["all_checks_ok"]},
        "deliverable_replay": {"path": "results/evaluation/operational_resume_40204378896/deliverable_verification_replay_40204378896.json",
                               "sha256": rep_sha, "status": rep["status"], "all_checks_ok": rep["all_checks_ok"]},
    }
    print(json.dumps(out, indent=2))
    return 0 if diag["all_checks_ok"] and snap["all_checks_ok"] and rep["all_checks_ok"] else 1


def finalize() -> int:
    state = load_json(REPO / "state/evaluation.json")
    lane = load_json(REPO / "evaluation/state/evaluation.json")
    inst = verify_instrument_records()
    state_checks = [
        check("root_github_run_is_current", state.get("github_run") == int(RUN_ID), observed=state.get("github_run")),
        check("lane_github_run_is_current", lane.get("github_run") == int(RUN_ID), observed=lane.get("github_run")),
        check("direction_version_68", state.get("direction_version") == 68 and lane.get("direction_version") == 68),
        check("accepted_run_unchanged", state.get("accepted_run_id") == PRIOR_ACCEPTED_RUN and lane.get("accepted_run_id") == PRIOR_ACCEPTED_RUN),
        check("continue_recommended_false", state.get("continue_recommended") is False and lane.get("continue_recommended") is False),
        check("root_lane_refs_counts_match",
              state.get("evidence_refs_n") == len(state.get("evidence_refs") or [])
              and lane.get("evidence_refs_n") == len(lane.get("evidence_refs") or []),
              root_n=state.get("evidence_refs_n"), root_len=len(state.get("evidence_refs") or []),
              lane_n=lane.get("evidence_refs_n"), lane_len=len(lane.get("evidence_refs") or [])),
        check("resume_block_present", bool(state.get("operational_resume_40204378896")) and bool(lane.get("operational_resume_40204378896"))),
        check("posture_flags_false", state.get("human_gate_ready") is False and state.get("machine_gate_ready") is False
              and lane.get("human_gate_ready") is False and lane.get("machine_gate_ready") is False),
    ]
    inv = artifact_inventory()
    all_missing = [x["path"] for x in inv if not x["exists"]]
    diagnosis = load_json(OUT / "diagnosis_40198184759.json")
    snap = load_json(OUT / "snapshot_integrity_40204378896.json")
    replay = load_json(OUT / "deliverable_verification_replay_40204378896.json")
    checks = diagnosis.get("checks", []) + snap.get("checks", []) + inst["checks"] + state_checks
    checks.append(check("artifact_inventory_complete", not all_missing, missing=all_missing, n=len(inv)))
    all_ok = all(c["ok"] for c in checks) and diagnosis.get("all_checks_ok") and snap.get("all_checks_ok") and replay.get("all_checks_ok")
    summary = {
        "schema": "lex-evaluation-operational-resume-summary/1",
        "lane": "evaluation",
        "run_id": RUN_ID,
        "resumed_run_id": RESUMED_RUN_ID,
        "generated_at_utc": GENERATED_AT_UTC,
        "status": "AUDIT_READY_PENDING_INDEPENDENT_AUDIT" if all_ok else "RESUME_DIVERGENCE",
        "all_checks_ok": all_ok,
        "n_checks": len(checks),
        "n_checks_ok": sum(1 for c in checks if c["ok"]),
        "failed_checks": [c["check"] for c in checks if not c["ok"]],
        "diagnosis": {"path": "results/evaluation/operational_resume_40204378896/diagnosis_40198184759.json",
                      "classification": diagnosis.get("classification"),
                      "all_checks_ok": diagnosis.get("all_checks_ok"),
                      "sha256": sha256_file(OUT / "diagnosis_40198184759.json")},
        "snapshot_integrity": {"path": "results/evaluation/operational_resume_40204378896/snapshot_integrity_40204378896.json",
                               "all_checks_ok": snap.get("all_checks_ok"),
                               "sha256": sha256_file(OUT / "snapshot_integrity_40204378896.json")},
        "deliverable_replay": {"path": "results/evaluation/operational_resume_40204378896/deliverable_verification_replay_40204378896.json",
                               "status": replay.get("status"), "all_checks_ok": replay.get("all_checks_ok"),
                               "n_checks": replay.get("n_checks"), "n_checks_ok": replay.get("n_checks_ok"),
                               "sha256": sha256_file(OUT / "deliverable_verification_replay_40204378896.json")},
        "instruments": {name: {"path": str(p.relative_to(REPO)),
                               "sha256": sha256_file(p) if p.is_file() else None,
                               "verdict": (load_json(p).get("verdict") if p.is_file() else None)}
                        for name, p in {
                            "state_integrity_gate": OUT / "state_integrity_gate_40204378896.json",
                            "nested_evidence_refs": OUT / "nested_refs/40204378896_nested_evidence_refs.json",
                            "pytest_targeted": OUT / "pytest_targeted_40204378896.json",
                            "write_scope": OUT / "write_scope_40204378896.json",
                        }.items()},
        "preserved_deliverables": {
            "item_1_correction_of_record": "PRESENT_AND_VERIFIED (measurement unchanged; CC6/CC7 closed by direct object verification at the current mount)",
            "item_2_post_repair_family": "NOT_YET_DISCRIMINATING (10/15 member-for-member; multiplicity parity false; post-repair record NOT_MEASURED_VACUOUS on pin drift; no synthetic stand-in)",
            "measurement_of_record": "results/evaluation/minimal_retrieval_ca_benchmark/40182692670.json PRODUCT_FALSIFIED (unchanged)",
            "gate_falsifiability_instrument": "results/evaluation/retrieval_counter_authority_benchmark/40175266143.json BENCHMARK_VALID_NO_FALSIFICATION (unchanged)",
            "accepted_eval_run": PRIOR_ACCEPTED_RUN,
        },
        "posture": {
            "direction_version": 68,
            "accepted_run_id": PRIOR_ACCEPTED_RUN,
            "continue_recommended": False,
            "new_same_question_cycle": False,
            "universal_174k_rerun": False,
            "human_gate_ready": False,
            "machine_gate_ready": False,
            "owner_decision_required": False,
            "do_not_serve_orders": "both stand",
        },
        "claim_ceiling": "Operational-resume verification only. It preserves the accepted evaluation cycle 40159747851 and the 40105794124 measurement, keeps item (2) NOT_YET_DISCRIMINATING, moves no frozen bar, issues no serve verdict, lifts no DO-NOT-SERVE order and opens no new same-question cycle.",
    }
    write_json(OUT / "summary_40204378896.json", summary)
    audit_index = {
        "schema": "lex-evaluation-operational-resume-audit-index/1",
        "lane": "evaluation",
        "run_id": RUN_ID,
        "resumed_run_id": RESUMED_RUN_ID,
        "generated_at_utc": GENERATED_AT_UTC,
        "purpose": "One-page, hash-indexed map from each claim to its committed artifact and exact executable check. It is the compact audit entry point for the independent auditor; it does not replace independent recomputation.",
        "claim_to_artifact": {
            "orchestration_failure_is_quantum_not_producer": ["results/evaluation/operational_resume_40204378896/diagnosis_40198184759.json",
                                                              "results/evaluation/operational_resume_40204378896/run_40198184759_api.json",
                                                              "results/evaluation/operational_resume_40204378896/jobs_40198184759_api.json"],
            "snapshot_preserved": ["results/evaluation/operational_resume_40204378896/snapshot_integrity_40204378896.json",
                                   "results/evaluation/operational_resume_40192868113/manifest_40192868113.json"],
            "item_1_correction_of_record": ["results/evaluation/operational_resume_40204378896/deliverable_verification_replay_40204378896.json",
                                            "results/evaluation/operational_resume_40204378896/provenance_fetch_record_40204378896.json",
                                            "reports/evaluation/BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md",
                                            "reports/evaluation/CORRECTION_FOLLOWUP_CITATION_40198184759.md",
                                            "results/evaluation/bypass_clause_correction/40144816305.json",
                                            "results/audit/evaluation/CYCLE_40133253347_GATE.json"],
            "item_2_not_yet_discriminating": ["results/evaluation/operational_resume_40204378896/deliverable_verification_replay_40204378896.json",
                                              "results/evaluation/post_repair_family_ca_falsifier/40162507752.json",
                                              "evaluation/POST_REPAIR_FAMILY_CA_FALSIFIER_40134202991_HYPOTHESIS_V1.json"],
            "state_and_scope_consistent": ["results/evaluation/operational_resume_40204378896/state_integrity_gate_40204378896.json",
                                           "results/evaluation/operational_resume_40204378896/nested_refs/40204378896_nested_evidence_refs.json",
                                           "results/evaluation/operational_resume_40204378896/pytest_targeted_40204378896.json",
                                           "results/evaluation/operational_resume_40204378896/write_scope_40204378896.json"],
            "posture_unchanged": ["state/evaluation.json", "evaluation/state/evaluation.json",
                                  "results/evaluation/operational_resume_40204378896/summary_40204378896.json"],
        },
        "exact_commands": [
            "python3 evaluation/operational_resume_40204378896.py prepare",
            "python3 -m evaluation.no_pytest_runner --run-id 40204378896 --test-file tests/evaluation/test_minimal_retrieval_ca_benchmark.py --test-file tests/evaluation/test_nested_evidence_refs_guard.py --test-file tests/evaluation/test_state_integrity_gate.py --test-file tests/evaluation/test_post_repair_family_ca_falsifier.py --out results/evaluation/operational_resume_40204378896/pytest_targeted_40204378896.json",
            "python3 evaluation/nested_evidence_refs_guard.py --run-id 40204378896 --out-dir results/evaluation/operational_resume_40204378896/nested_refs",
            "python3 -m evaluation.state_integrity_gate --run-id 40204378896 --out results/evaluation/operational_resume_40204378896/state_integrity_gate_40204378896.json",
            "python3 -m evaluation.snapshot_audit.write_scope --lane evaluation --out results/evaluation/operational_resume_40204378896/write_scope_40204378896.json",
            "python3 evaluation/operational_resume_40204378896.py finalize",
        ],
        "auditor_shortcut": "Run `python3 evaluation/operational_resume_40204378896.py finalize` in the producer worktree; it reads every record above and prints the pass/fail summary. It will refuse an audit-ready verdict if any record, hash or posture check fails.",
        "artifact_inventory": inv,
        "summary_sha256": sha256_file(OUT / "summary_40204378896.json"),
        "claim_ceiling": "Index only; every entry resolves to a committed artifact. It makes no measurement claim of its own.",
    }
    write_json(OUT / "AUDIT_INDEX_40204378896.json", audit_index)
    print(json.dumps({"status": summary["status"], "all_checks_ok": all_ok,
                      "n_checks": len(checks), "n_checks_ok": summary["n_checks_ok"],
                      "failed_checks": summary["failed_checks"],
                      "summary": "results/evaluation/operational_resume_40204378896/summary_40204378896.json",
                      "audit_index": "results/evaluation/operational_resume_40204378896/AUDIT_INDEX_40204378896.json"}, indent=2))
    return 0 if all_ok else 1


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    mode = argv[0] if argv else "prepare"
    if mode == "prepare":
        return prepare()
    if mode == "finalize":
        return finalize()
    print(f"unknown mode {mode!r}; use prepare|finalize", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
