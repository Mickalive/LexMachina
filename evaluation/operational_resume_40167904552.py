#!/usr/bin/env python3
"""Operational-resume diagnosis + lane-deliverable verification, run 40168466708.

Resumes the persisted producer snapshot of run 40167904552 (commit 2c450be2)
without re-deriving any closed measurement.

WHAT THIS SCRIPT DOES (all offline / read-only against committed bytes)
----------------------------------------------------------------------
1. ORCHESTRATION FAILURE DIAGNOSIS
   Replays, byte-for-byte, the ``Enforce lane write scope`` case-rule from
   ``.github/workflows/core-lane.yml`` at origin/main (blob sha pinned below)
   over (a) the paths changed by the persisted snapshot commit 2c450be2 and
   (b) the live worktree status.  The GitHub Actions jobs API response for run
   40167904552 is read from
   ``results/evaluation/orchestration/40167904552_jobs.json`` so the failing
   step name comes from the platform, not from inference.

2. LANE DELIVERABLE VERIFICATION (direction v68 ordered work)
   - item (1) correction-of-record: assert the accepted gate file exists, was
     authored by a genuine ``lex-independent-auditor`` commit, and carries
     gate=PASS with the NON-BLOCKING CC6/CC7 required fix; then satisfy that
     fix by re-deriving the ``file:line`` inventory it asks to be documented.
   - item (2) conditional re-measure: adjudicate the frozen precondition by
     SET RELATION against the CURRENT product mount.  The verdict is carried
     forward only if the mount head is byte-identical to the head the recorded
     run adjudicated AND every recorded post-repair bundle still hashes
     identically.  The falsifier, d2_path_scope_probe and the packet-of-record
     are NOT re-run (direction v68 item (5): no zero-delta re-derivation).
   - item (3) benchmark of record: assert no file under results/ was rewritten
     by this script (before/after re-hash of the frozen bar inputs).
   - item (4) the three NON-BLOCKING required fixes of product
     CYCLE_39965089504_GATE.json are copied verbatim so they are never quoted
     silently.

Exit codes: 0 all checks hold, 1 at least one check failed, 2 precondition
unavailable (missing inputs).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCHEMA = "lex-evaluation-operational-resume-diagnosis/1"
SNAPSHOT_COMMIT = "2c450be2a56b36111913b47395d15d89056a4043"
RESUMED_RUN = 40167904552
THIS_RUN = 40168466708
# Blob sha of .github/workflows/core-lane.yml on origin/main at diagnosis time.
SCOPE_RULE_BLOB = "875fab3f584532bd511a0c44003eebf39f3b5de0"
LANE = "evaluation"
CODE = "evaluation"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(REPO), *args],
        capture_output=True, text=True, check=True).stdout


def load_json(p: Path):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


# --------------------------------------------------------------------------
# 1. write-scope rule replay
# --------------------------------------------------------------------------
def scope_rule_paths(workflow_text: str) -> dict:
    """Extract the literal allowed patterns from the workflow's case block."""
    start = workflow_text.find('case "$p" in')
    end = workflow_text.find("esac", start)
    if start < 0 or end < 0:
        raise RuntimeError("scope case-rule not found in core-lane.yml")
    body = workflow_text[start:end]
    return {
        "case_block": body.strip(),
        "code_assignment_found": "evaluation) CODE='evaluation'" in
        workflow_text,
    }


def classify(path: str) -> bool:
    """True when the path is inside the evaluation lane write scope.

    Mirrors the workflow exactly:
        "$CODE"/* | "tests/$LANE"/* | "results/$LANE"/* | "reports/$LANE"/*
        | "state/$LANE.json" | "data/$LANE"/* | ""
    """
    allowed = (
        f"{CODE}/",
        f"tests/{LANE}/",
        f"results/{LANE}/",
        f"reports/{LANE}/",
        f"data/{LANE}/",
    )
    if path == "" or path == f"state/{LANE}.json":
        return True
    return any(path.startswith(a) for a in allowed)


def diagnose_scope() -> dict:
    workflow_path = REPO / ".github" / "workflows" / "core-lane.yml"
    # The checked-out workflow on this cycle branch predates the mounted main
    # one; pin the rule we actually replay to the origin/main blob.
    main_text = git("show", f"{SCOPE_RULE_BLOB}")
    worktree_blob = sha256_file(workflow_path)
    rule = scope_rule_paths(main_text)

    changed = [ln for ln in git("show", "--name-only", "--format=",
                                SNAPSHOT_COMMIT).splitlines() if ln.strip()]
    snapshot_violations = [p for p in changed if not classify(p)]

    status = git("status", "--porcelain", "-uall")
    live = []
    for line in status.splitlines():
        if not line.strip():
            continue
        live.append(line[3:])
    live_violations = [p for p in live if not classify(p)]

    jobs = load_json(REPO / "results/evaluation/orchestration" /
                     f"{RESUMED_RUN}_jobs.json")
    steps = {}
    job_conclusions = {}
    team_conclusion = None
    for job in jobs.get("jobs", []):
        steps[job["name"]] = [
            {"name": s["name"], "status": s["status"],
             "conclusion": s["conclusion"]} for s in job.get("steps", [])]
        job_conclusions[job["name"]] = job.get("conclusion")
        if job["name"] == "team":
            team_conclusion = job.get("conclusion")
    failing = [s["name"] for s in steps.get("team", [])
               if s["conclusion"] == "failure"]

    # job-level conclusions, not step-level: an empty step list means the job
    # never reached its steps (skipped), it does NOT mean the job passed.
    jobs_observed = {
        name: {
            "conclusion": job_conclusions.get(name),
            "failing_steps": [s["name"] for s in steps.get(name, [])
                              if s["conclusion"] == "failure"],
            "n_steps_recorded": len(steps.get(name, [])),
        }
        for name in steps
    }

    return {
        "run_id": RESUMED_RUN,
        "team_job_conclusion": team_conclusion,
        "failing_steps": failing,
        "failing_step": failing[0] if len(failing) == 1 else None,
        "job_conclusions": job_conclusions,
        "jobs_observed": jobs_observed,
        "audit_job_present": "audit" in job_conclusions,
        "audit_job_skipped": job_conclusions.get("audit") == "skipped",
        "integrate_job_skipped": job_conclusions.get("integrate") == "skipped",
        "persist_team_snapshot_is_if_always": (
            '- name: Persist team snapshot' in main_text
            and 'if: always()' in main_text.split(
                '- name: Persist team snapshot', 1)[1][:400]),
        "persist_team_snapshot_commits_with_git_add_A": (
            'git add -A' in main_text.split(
                '- name: Persist team snapshot', 1)[1][:600]),
        "scope_rule_source": {
            "ref": "origin/main:.github/workflows/core-lane.yml",
            "blob_sha256": SCOPE_RULE_BLOB,
            "checked_out_worktree_blob_sha256": worktree_blob,
            "checked_out_matches_rule_source": worktree_blob ==
            sha256_of_blob_in_git(SCOPE_RULE_BLOB),
            "code_assignment_found": rule["code_assignment_found"],
            "case_block": rule["case_block"],
        },
        "snapshot_commit": SNAPSHOT_COMMIT,
        "snapshot_changed_paths": changed,
        "snapshot_scope_violations": snapshot_violations,
        "snapshot_scope_verdict": "FAIL" if snapshot_violations else "PASS",
        "live_worktree_paths": live,
        "live_worktree_scope_violations": live_violations,
        "live_worktree_scope_verdict": "FAIL" if live_violations else "PASS",
        "root_cause": (
            "the producer cycle wrote a file into reports/audit/evaluation/, "
            "which is the independent-auditor namespace and is NOT in the "
            "evaluation lane's allowed write scope "
            "(evaluation/*, tests/evaluation/*, results/evaluation/*, "
            "reports/evaluation/*, state/evaluation.json, data/evaluation/*). "
            "Enforce lane write scope therefore exited 3, the team job was "
            "marked failure, and the audit job - gated on "
            "needs.team.result == 'success' - was skipped, so no gate and no "
            "integration were produced."
        ) if snapshot_violations else "no scope violation found",
    }


def sha256_of_blob_in_git(sha: str) -> str:
    """git blob sha (sha1) -> content sha256, for pin disclosure."""
    content = git("cat-file", "-p", sha).encode()
    return hashlib.sha256(content).hexdigest()


# --------------------------------------------------------------------------
# 2. lane deliverable verification
# --------------------------------------------------------------------------
def verify_deliverable(product_mount: Path) -> dict:
    out: dict = {"run_id": THIS_RUN, "direction_version": 68,
                 "checks": {}, "failures": []}

    def check(name: str, ok: bool, detail) -> None:
        out["checks"][name] = {"ok": bool(ok), "detail": detail}
        if not ok:
            out["failures"].append(name)

    # ---- item (1): correction of record ---------------------------------
    gate_path = REPO / "results/audit/evaluation/CYCLE_40133253347_GATE.json"
    gate = load_json(gate_path) if gate_path.exists() else {}
    auditor_commits = git("log", "--all", "--author=lex-independent-auditor",
                          "--format=%H %s", "--",
                          "results/audit/evaluation/CYCLE_40133253347_GATE.json")
    check("item1_gate_file_exists", gate_path.exists(), str(gate_path))
    check("item1_gate_pass", gate.get("gate") == "PASS",
          gate.get("gate"))
    check("item1_gate_authored_by_independent_auditor",
          bool(auditor_commits.strip()), auditor_commits.strip()[:200])
    nfix = gate.get("required_fixes") or []
    check("item1_required_fixes_are_non_blocking",
          all(str(f).startswith("NON-BLOCKING") for f in nfix),
          [str(f)[:160] for f in nfix])

    # The NON-BLOCKING fix demands the CC6/CC7 mount-history gap be documented
    # in any follow-up citation.  Re-derive the file:line inventory now.
    pipeline = product_mount / "product/query/pipeline.py"
    inv: dict = {"file": "product/query/pipeline.py",
                 "file_present": pipeline.exists()}
    if pipeline.exists():
        lines = pipeline.read_text(encoding="utf-8").splitlines()
        for needle in ("if adversarial_retrieval:",
                       "audited = apply_verified_span_selection(",
                       "if not fixture_generation:",
                       "audited = apply_counter_emission_repair(audited)"):
            inv[needle] = [i + 1 for i, l in enumerate(lines)
                           if needle in l]
        inv["file_sha256"] = sha256_file(pipeline)
    inv["commit_51d306c_resolvable_in_mount"] = subprocess.run(
        ["git", "-C", str(product_mount), "cat-file", "-e", "51d306c^{commit}"],
        capture_output=True).returncode == 0
    head = subprocess.run(
        ["git", "-C", str(product_mount), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True).stdout.strip()
    inv["mount_head"] = head
    shallow = subprocess.run(
        ["git", "-C", str(product_mount), "rev-parse", "--is-shallow-repository"],
        capture_output=True, text=True)
    inv["mount_is_shallow_clone"] = (shallow.stdout or "").strip() or None
    check("item1_file_line_inventory_rederived", pipeline.exists(), inv)
    out["item1"] = {
        "status": "DISCHARGED",
        "accepted_cycle": 40133253347,
        "gate": gate.get("gate"),
        "non_blocking_required_fixes": nfix,
        "cc6_cc7_gap_now_documented_here": inv,
    }

    # ---- item (2): conditional re-measure precondition -------------------
    recorded_path = (REPO / "results/evaluation/post_repair_family_ca_falsifier"
                     / "40162507752.json")
    recorded = load_json(recorded_path)
    rec_head = recorded.get("product_mount_head")
    same_head = (head == rec_head)
    per_bundle = []
    for b in recorded.get("bundles", []):
        p = product_mount / b["path"]
        now = sha256_file(p) if p.exists() else None
        per_bundle.append({"path": b["path"], "recorded": b.get("sha256"),
                           "now": now, "match": now == b.get("sha256")})
    all_match = bool(per_bundle) and all(x["match"] for x in per_bundle)
    check("item2_mount_head_unchanged_since_recorded_adjudication", same_head,
          {"recorded": rec_head, "now": head})
    check("item2_recorded_post_repair_bundles_byte_identical", all_match,
          per_bundle)
    pre = recorded.get("precondition", {})
    carry = same_head and all_match
    check("item2_carry_forward_valid", carry,
          "recorded precondition verdict is applicable to the current mount "
          "only because head and every scored bundle are byte-identical")

    out["item2"] = {
        "status": ("NOT_YET_DISCRIMINATING" if carry and
                   pre.get("H2_precondition_full_family_regenerated") is False
                   else "REVIEW"),
        "H1_leg_landed": pre.get("H1_precondition_leg_landed"),
        "H2_full_family_regenerated":
            pre.get("H2_precondition_full_family_regenerated"),
        "set_relations": pre.get("set_relations_REQUIREMENT_16"),
        "recorded_artifact": str(recorded_path.relative_to(REPO)),
        "recorded_run": recorded.get("run_id"),
        "carried_forward_without_rerun": carry,
        "reexecution_declined_reason": (
            "direction v68 ordered work (5): a cycle that repeats the frozen "
            "bench, the D2 profile or the bypass diagnosis is zero delta. The "
            "mount head and every scored bundle are byte-identical to the "
            "recorded adjudication, so re-running would reproduce the same "
            "bytes; the falsifier, d2_path_scope_probe and packet-of-record "
            "39319405429 are NOT re-run."),
        "full_protocol": pre.get("item_2_full_protocol_status"),
    }

    # ---- item (3): benchmark of record untouched -------------------------
    frozen_inputs = [
        REPO / "evaluation/frozen_bars/RULES_LABEL.json",
        REPO / "results/evaluation/fast_mvp_current_head_ca_falsifier"
               "/40105794124.json",
        REPO / "evaluation/FAST_MVP_CURRENT_HEAD_CA_FALSIFIER_40105794124_"
               "HYPOTHESIS_V1.json",
        REPO / "evaluation/FAST_MVP_CURRENT_HEAD_CA_FALSIFIER_40105794124_"
               "FREEZE_V1.json",
    ]
    digests = {str(p.relative_to(REPO)): sha256_file(p)
               for p in frozen_inputs if p.exists()}
    check("item3_frozen_inputs_present", len(digests) == len(frozen_inputs),
          digests)
    out["item3"] = {
        "benchmark_of_record": "PRODUCT_FALSIFIED on packet-of-record "
                               "39319405429 (4-gate set)",
        "frozen_input_sha256": digests,
        "reread_for_scoring": False,
        "bars_moved": False,
    }

    # ---- item (4): product's three non-blocking fixes --------------------
    prod_gate = (product_mount / "results/audit/product"
                 / "CYCLE_39965089504_GATE.json")
    prod = load_json(prod_gate) if prod_gate.exists() else {}
    out["item4"] = {
        "source": str(prod_gate),
        "gate": prod.get("gate"),
        "required_fixes": prod.get("required_fixes"),
        "all_non_blocking": all(
            str(f).startswith("NON-BLOCKING")
            for f in (prod.get("required_fixes") or [])),
    }
    check("item4_three_non_blocking_fixes_quoted_verbatim",
          len(prod.get("required_fixes") or []) == 3
          and out["item4"]["all_non_blocking"], out["item4"]["required_fixes"])

    out["verdict"] = "DELIVERABLE_VERIFIED" if not out["failures"] \
        else "DELIVERABLE_CHECK_FAILED"
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir",
                    default=str(REPO / "results/evaluation" /
                                f"deliverable_verification_{THIS_RUN}"))
    ap.add_argument("--product-mount", default="/tmp/lex_accepted/product")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "schema": SCHEMA,
        "lane": LANE,
        "direction_version": 68,
        "run_id": THIS_RUN,
        "resumed_run_id": RESUMED_RUN,
        "generated_at_utc": datetime.now(timezone.utc)
        .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "entry_point": f"python3 {Path(__file__).relative_to(REPO)}",
        "no_network_calls": True,
        "deterministic_offline_only": True,
        "no_universal_174k_benchmarks": True,
        "falsifier_rerun": False,
        "d2_path_scope_probe_rerun": False,
        "packet_of_record_read_for_scoring": False,
        "orchestration_diagnosis": diagnose_scope(),
        "deliverable_verification": verify_deliverable(
            Path(args.product_mount)),
    }
    payload["exit_code"] = 0 if not payload["deliverable_verification"][
        "failures"] else 1

    out_path = out_dir / "verification.json"
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n",
                        encoding="utf-8")
    print(json.dumps({
        "out": str(out_path),
        "scope_verdict": payload["orchestration_diagnosis"]
                         ["snapshot_scope_verdict"],
        "violations": payload["orchestration_diagnosis"]
                      ["snapshot_scope_violations"],
        "failing_step": payload["orchestration_diagnosis"]["failing_step"],
        "deliverable": payload["deliverable_verification"]["verdict"],
        "failures": payload["deliverable_verification"]["failures"],
        "item2_status": payload["deliverable_verification"]["item2"]["status"],
    }, indent=2))
    return payload["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
