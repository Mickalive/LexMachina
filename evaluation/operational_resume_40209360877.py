#!/usr/bin/env python3
"""Operational-resume verifier and compact audit pack for evaluation run 40209360877.

Base: the persisted producer snapshot of run 40204378896 (commit 14b9e9cf).
Adapted from evaluation/operational_resume_40204378896.py (REUSE-FIRST: the
prior resume's structure, check vocabulary and claim ceiling are reused; only
run ids, the diagnosed run and the new verification commands change).

This resume does NOT start over and does NOT open a new same-question cycle:

  * it diagnoses the orchestration failure of run 40204378896 from the public
    GitHub run/jobs JSON and the checked-in work-quantum wrapper, and shows the
    identical signature on the three earlier runs;
  * it proves the 40204378896 audit-ready pack is preserved byte-for-byte;
  * it re-executes the smallest executable retrieval/counter-authority
    falsifier (already frozen, invoked through its accepted engine) in scratch
    and compares it field-by-field with the committed measurement of record;
  * it runs the lane's state/scope/test instruments under this run id with
    measured wall time, and builds one hash-indexed audit pack whose total
    measured verification time is published so the recurring audit starvation
    cannot be blamed on pack size.

Claim ceiling: operational-resume verification only. No frozen bar, rubric,
threshold, verdict contract, serve verdict or admission flag is touched.

Usage (from the producer/team worktree):
    python3 evaluation/operational_resume_40209360877.py verify
    python3 evaluation/operational_resume_40209360877.py prepare
    python3 evaluation/operational_resume_40209360877.py finalize

`verify` runs the pre-registered commands as subprocesses, times each one and
writes command_runtimes_40209360877.json plus stdout logs.
`prepare` writes the diagnosis, prior-pack integrity and falsifier comparison.
`finalize` writes summary_40209360877.json and AUDIT_INDEX_40209360877.json.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

RUN_ID = "40209360877"
RESUMED_RUN_ID = "40204378896"
STARVATION_RUNS = ("40187594111", "40192868113", "40198184759", "40204378896")
PRIOR_RESUME_RUN = "40198184759"
SNAPSHOT_COMMIT = "14b9e9cf9d8c4d88f378fd8ae4281d3cbb18c2f5"
PRIOR_SNAPSHOT_COMMIT = "251a6f5967c653d3ca93bf0a2d3ad7a1dd3f875e"
ACCEPTED_RUN = 40159747851
ACCEPT_COMMIT = "9be8a7d5b3a4b84eb45da6160bf90620f7d81d40"
DIRECTION_VERSION = 68
GENERATED_AT_UTC = "2026-10-25T16:12:00Z"

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "results/evaluation/operational_resume_40209360877"
API = OUT / "api"
LOGS = OUT / "logs"
PRIOR_PACK = REPO / "results/evaluation/operational_resume_40204378896"
MEASUREMENT_OF_RECORD = REPO / "results/evaluation/minimal_retrieval_ca_benchmark/40182692670.json"
HYPOTHESIS = REPO / "evaluation/OPERATIONAL_RESUME_40209360877_HYPOTHESIS_V1.json"
FREEZE = REPO / "evaluation/OPERATIONAL_RESUME_40209360877_FREEZE_V1.json"
REPORT = REPO / "reports/evaluation/OPERATIONAL_RESUME_40209360877_AUDIT_READY.md"
FROZEN_LABEL_SHA = "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"
FROZEN_GEOMETRY_SHA = "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633"
MEASUREMENT_OF_RECORD_SHA = "fd29a395f8b5307d67abeb79335337250518cc6de171a26ddbf09768840ade73"
API_BASE = "https://api.github.com/repos/Mickalive/LexMachina/actions/runs"

# Pre-registered commands (freeze file): (key, argv, expected exit code, note)
COMMANDS: list[tuple[str, list[str], int, str]] = [
    ("falsifier_replay_postfreeze",
     [sys.executable, "-m", "evaluation.minimal_retrieval_ca_benchmark",
      "--run-id", RUN_ID,
      "--out-dir", str(OUT / "falsifier_replay_postfreeze"),
      "--report-dir", str(OUT / "falsifier_replay_postfreeze")],
     1, "expected exit 1 = PRODUCT_FALSIFIED (VERDICT_CONTRACT); exit 0 would be PASS_NO_FALSIFICATION, exit 2 vacuous"),
    ("state_integrity_gate",
     [sys.executable, "-m", "evaluation.state_integrity_gate", "--run-id", RUN_ID,
      "--out", str(OUT / f"state_integrity_gate_{RUN_ID}.json")], 0, "ALL_CHECKS_PASS 11/11"),
    ("nested_evidence_refs_guard",
     [sys.executable, "evaluation/nested_evidence_refs_guard.py", "--run-id", RUN_ID,
      "--out-dir", str(OUT / "nested_refs")], 0, "NESTED_REFS_RESOLVED, 0 unresolved"),
    ("write_scope",
     [sys.executable, "-m", "evaluation.snapshot_audit.write_scope", "--lane", "evaluation",
      "--out", str(OUT / f"write_scope_{RUN_ID}.json")], 0, "SCOPE_CLEAN, 0 bad"),
    ("pytest_targeted",
     [sys.executable, "-m", "evaluation.no_pytest_runner", "--run-id", RUN_ID,
      "--test-file", "tests/evaluation/test_minimal_retrieval_ca_benchmark.py",
      "--test-file", "tests/evaluation/test_nested_evidence_refs_guard.py",
      "--test-file", "tests/evaluation/test_state_integrity_gate.py",
      "--test-file", "tests/evaluation/test_post_repair_family_ca_falsifier.py",
      "--out", str(OUT / f"pytest_targeted_{RUN_ID}.json")], 0, "SHIM_PASS, 0 failed, 0 absent"),
    ("pytest_multilingual_provenance",
     [sys.executable, "-m", "evaluation.no_pytest_runner", "--run-id", RUN_ID,
      "--test-file", "tests/evaluation/test_stand_ready_multilingual_probe.py",
      "--test-file", "tests/evaluation/test_cross_lingual_alignment_v10.py",
      "--test-file", "tests/evaluation/test_disclosure_provenance_crosscheck.py",
      "--test-file", "tests/evaluation/test_fast_mvp_retrieval_recall_benchmark.py",
      "--test-file", "tests/evaluation/test_boilerplate_resistance_real.py",
      "--test-file", "tests/evaluation/test_nested_evidence_refs_guard.py",
      "--out", str(OUT / f"pytest_multilingual_provenance_{RUN_ID}.json")], 0,
     "SHIM_PASS, 0 failed; numpy import error and class-based collection gaps are disclosed, never counted as passes"),
]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, indent=2, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def git(*args: str, cwd: Path = REPO) -> tuple[int, str, str]:
    p = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, timeout=120)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def check(name: str, ok: bool, **detail) -> dict:
    return {"check": name, "passed": bool(ok), "detail": detail}


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------- api envelopes
def load_or_fetch_api(kind: str, run_id: str, capture: bool) -> dict:
    """kind is 'run' or 'jobs'. Committed envelope is authoritative for replay."""
    API.mkdir(parents=True, exist_ok=True)
    path = API / f"{kind}_{run_id}_api.json"
    if path.is_file() and not capture:
        return {"path": str(path.relative_to(REPO)), "source": "committed_envelope_replay",
                "envelope": load_json(path), "network": False}
    url = f"{API_BASE}/{run_id}" + ("/jobs?per_page=100" if kind == "jobs" else "")
    try:
        p = subprocess.run(["curl", "-sf", "--max-time", "30", url],
                           capture_output=True, timeout=60)
        if p.returncode != 0 or not p.stdout:
            raise RuntimeError(f"curl rc={p.returncode}")
        envelope = json.loads(p.stdout.decode("utf-8"))
        path.write_bytes(p.stdout)
        return {"path": str(path.relative_to(REPO)), "source": "public_unauthenticated_rest_capture",
                "envelope": envelope, "network": True, "url": url}
    except Exception as exc:  # offline fallback
        if path.is_file():
            return {"path": str(path.relative_to(REPO)), "source": "committed_envelope_replay_after_fetch_error",
                    "envelope": load_json(path), "network": False, "fetch_error": repr(exc)}
        return {"path": None, "source": "unavailable", "envelope": None, "network": False,
                "fetch_error": repr(exc)}


def _job(jobs: dict, name: str) -> dict | None:
    for j in jobs.get("jobs", []):
        if j.get("name") == name:
            return j
    return None


def _step(job: dict, name: str) -> dict | None:
    for s in job.get("steps", []):
        if s.get("name") == name:
            return s
    return None


def _secs(a: str | None, b: str | None) -> float | None:
    if not a or not b:
        return None
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    return (datetime.strptime(b, fmt) - datetime.strptime(a, fmt)).total_seconds()


def audit_branch_probe(run_id: str) -> dict:
    ref = f"refs/heads/cycle/core/evaluation/{run_id}/audit"
    rc, out, err = git("ls-remote", "--heads", "origin", ref)
    if rc != 0:
        return {"ref": ref, "probe": "git ls-remote failed", "error": err, "exists": None}
    return {"ref": ref, "probe": "git ls-remote --heads origin", "exists": bool(out),
            "stdout": out or "(empty)"}


def wrapper_quantum_facts() -> dict:
    """Read the quantum mechanism from origin/main's wrapper (control plane, never edited here)."""
    rc, text, err = git("show", "origin/main:.github/scripts/run-ox-with-retry.sh")
    if rc != 0:
        return {"available": False, "error": err}
    lines = text.splitlines()
    wanted = {
        "quantum_constant": "WORK_QUANTUM_SECONDS=",
        "poll_interval": "sleep 15",
        "kill_condition": "now - start >= WORK_QUANTUM_SECONDS",
        "exit_78_return": "return 78",
        "expired_warning": "LEX_WORK_QUANTUM_EXPIRED",
    }
    hits = {}
    for key, needle in wanted.items():
        hits[key] = [{"line": i + 1, "text": ln.strip()}
                     for i, ln in enumerate(lines) if needle in ln]
    quantum = None
    m = re.search(r"WORK_QUANTUM_SECONDS[^0-9]*([0-9]+)", text)
    if m:
        quantum = int(m.group(1))
    poll = None
    for h in hits["poll_interval"]:
        mm = re.search(r"sleep ([0-9]+)", h["text"])
        if mm:
            poll = int(mm.group(1))
    return {"available": True, "ref": "origin/main:.github/scripts/run-ox-with-retry.sh",
            "lines": hits, "quantum_seconds": quantum, "poll_seconds": poll,
            "quantum_divisible_by_poll": (quantum % poll == 0) if (quantum and poll) else None}


# --------------------------------------------------------------------- prepare
def build_diagnosis(capture: bool) -> dict:
    runs = []
    for rid in STARVATION_RUNS + (RUN_ID,):
        run_env = load_or_fetch_api("run", rid, capture)
        jobs_env = load_or_fetch_api("jobs", rid, capture)
        run = run_env["envelope"] or {}
        jobs = jobs_env["envelope"] or {}
        team = _job(jobs, "team") or {}
        audit = _job(jobs, "audit") or {}
        integrate = _job(jobs, "integrate") or {}
        resil = _job(jobs, "resilience") or {}
        ind = _step(audit, "Independent audit") or {}
        scope = _step(audit, "Enforce audit scope and read gate") or {}
        persist = _step(audit, "Persist audit snapshot") or {}
        team_steps = team.get("steps", [])
        duration = _secs(ind.get("started_at"), ind.get("completed_at"))
        row = {
            "run_id": rid,
            "run_name": run.get("name"),
            "run_status": run.get("status"),
            "run_conclusion": run.get("conclusion"),
            "run_created_at": run.get("created_at"),
            "team_job": {
                "conclusion": team.get("conclusion"),
                "started_at": team.get("started_at"),
                "completed_at": team.get("completed_at"),
                "n_steps": len(team_steps),
                "all_steps_success": bool(team_steps) and all(
                    s.get("conclusion") == "success" for s in team_steps),
                "step_conclusions": {s.get("name"): s.get("conclusion") for s in team_steps},
            },
            "audit_job": {
                "conclusion": audit.get("conclusion"),
                "started_at": audit.get("started_at"),
                "completed_at": audit.get("completed_at"),
                "failed_step": (ind or {}).get("name") if ind.get("conclusion") == "failure" else None,
                "independent_audit_step": {
                    "started_at": ind.get("started_at"),
                    "completed_at": ind.get("completed_at"),
                    "conclusion": ind.get("conclusion"),
                    "duration_seconds": duration,
                },
                "enforce_gate_step": {"status": scope.get("status"), "conclusion": scope.get("conclusion")},
                "persist_audit_step": {"status": persist.get("status"), "conclusion": persist.get("conclusion")},
            },
            "integrate_job": {"conclusion": integrate.get("conclusion")},
            "resilience_job": {"conclusion": resil.get("conclusion")},
            "api_sources": {"run": run_env["path"], "jobs": jobs_env["path"]},
        }
        runs.append(row)

    wrapper = wrapper_quantum_facts()
    durations = [r["audit_job"]["independent_audit_step"]["duration_seconds"]
                 for r in runs
                 if r["run_id"] in STARVATION_RUNS
                 and r["audit_job"]["independent_audit_step"]["duration_seconds"] is not None]
    branches = {rid: audit_branch_probe(rid) for rid in STARVATION_RUNS + (RUN_ID,)}
    quantum = wrapper.get("quantum_seconds")
    poll = wrapper.get("poll_seconds")

    obs = {
        "starvation_runs": list(STARVATION_RUNS),
        "independent_audit_durations_seconds": durations,
        "durations_all_equal": len(durations) == len(STARVATION_RUNS)
                               and len(set(durations)) == 1,
        "duration_value": durations[0] if durations else None,
        "quantum_seconds": quantum,
        "poll_seconds": poll,
        "predicted_step_duration": (quantum + 4) if quantum else None,
        "quantum_divisible_by_poll": wrapper.get("quantum_divisible_by_poll"),
        "max_poll_detection_delay_seconds": poll if poll else None,
        "observed_pre_agent_overhead_seconds": ((durations[0] - quantum)
                                                if (durations and quantum) else None),
        "audit_branches_exist": {k: v["exists"] for k, v in branches.items()},
        "any_audit_branch_exists": any(v["exists"] for k, v in branches.items() if k in STARVATION_RUNS),
    }

    resume_ev = _resume_dispatch_evidence()
    all_checks = [
        check("team_all_steps_success_every_starvation_run",
              all(r["team_job"]["all_steps_success"] for r in runs if r["run_id"] in STARVATION_RUNS)),
        check("audit_conclusion_failure_every_starvation_run",
              all(r["audit_job"]["conclusion"] == "failure" for r in runs if r["run_id"] in STARVATION_RUNS)),
        check("failing_step_is_independent_audit_every_starvation_run",
              all(r["audit_job"]["failed_step"] == "Independent audit"
                  for r in runs if r["run_id"] in STARVATION_RUNS)),
        check("durations_all_equal_and_within_quantum_window",
              obs["durations_all_equal"] and quantum is not None
              and all(quantum <= d <= quantum + (poll or 0) for d in durations),
              observed_seconds=durations, quantum=quantum, poll=poll,
              window=f"[{quantum}, {quantum + (poll or 0)}]"),
        check("gate_and_persist_steps_skipped_every_starvation_run",
              all(r["audit_job"]["enforce_gate_step"]["conclusion"] == "skipped"
                  and r["audit_job"]["persist_audit_step"]["conclusion"] == "skipped"
                  for r in runs if r["run_id"] in STARVATION_RUNS),
              note="GitHub reports a skipped step as status=completed, conclusion=skipped; "
                   "the conclusion column is the one that matters here"),
        check("integrate_skipped_every_starvation_run",
              all(r["integrate_job"]["conclusion"] == "skipped"
                  for r in runs if r["run_id"] in STARVATION_RUNS)),
        check("resilience_success_every_starvation_run",
              all(r["resilience_job"]["conclusion"] == "success"
                  for r in runs if r["run_id"] in STARVATION_RUNS)),
        check("no_audit_branch_for_any_starvation_run", not obs["any_audit_branch_exists"],
              branches={k: v for k, v in branches.items() if k in STARVATION_RUNS}),
        check("wrapper_quantum_mechanism_present",
              wrapper.get("available") and quantum == 2700 and poll == 15
              and wrapper.get("quantum_divisible_by_poll") is True, wrapper=wrapper),
        check("this_run_is_the_operational_resume_dispatch", resume_ev["ok"], evidence=resume_ev),
        check("current_run_team_job_still_in_progress_or_success",
              runs[-1]["team_job"]["conclusion"] in (None, "success")),
    ]
    failed = [c["check"] for c in all_checks if not c["passed"]]

    return {
        "schema": "lex-evaluation-operational-resume-diagnosis/1",
        "lane": "evaluation",
        "run_id": RUN_ID,
        "diagnosed_run_id": RESUMED_RUN_ID,
        "direction_version": DIRECTION_VERSION,
        "generated_at_utc": now_utc(),
        "failure_class": "ORCHESTRATION_WORK_QUANTUM_EXPIRED",
        "failure_class_confidence": "high",
        "failure_summary": (
            f"Run {RESUMED_RUN_ID}'s producer team job succeeded end-to-end and persisted snapshot "
            f"{SNAPSHOT_COMMIT}; its independent-audit job failed at step 'Independent audit' after "
            f"{obs['duration_value']}s (quantum {quantum}s + 4s step setup), the two later audit steps "
            f"were skipped, integrate was skipped and resilience dispatched this resume with "
            f"resume_from_run_id={RESUMED_RUN_ID}. The identical {obs['duration_value']}s signature now "
            f"appears on four consecutive runs ({', '.join(STARVATION_RUNS)}), no /audit ref exists for "
            "any of them, and the run therefore issued NO verdict. This is not a producer failure, not "
            "a validation failure, not a gate REVISE/BLOCKED and not a product defect."),
        "mechanism": {
            "source": "origin/main:.github/scripts/run-ox-with-retry.sh (control plane; recorded, never edited by this lane)",
            "quantum_seconds": quantum,
            "poll_seconds": poll,
            "kill_branch": "lines 180-187: sleep 15; if now-start>=WORK_QUANTUM_SECONDS -> LEX_WORK_QUANTUM_EXPIRED -> kill_agent_group -> return 78",
            "exit_code": 78,
            "why_exactly_2704_seconds": (
                f"the quantum ({quantum}) is an exact multiple of the poll interval ({poll}), so the "
                "boundary test first fires exactly 2700s after the agent session starts; the GitHub step "
                "clock also includes ~4s of step setup, giving the observed 2704.0s. Four identical "
                "durations is the signature of a programmatic kill, not random provider behaviour."),
            "log_evidence_available": False,
            "log_evidence_note": ("GitHub job-log endpoint returns HTTP 403 unauthenticated and GH_TOKEN "
                                  "is unset in this producer job; the mechanism is inferred from duration "
                                  "arithmetic plus the checked-in wrapper, and is labelled inference, not "
                                  "a quoted crash line."),
        },
        "runs": runs,
        "audit_branch_probes": branches,
        "observation_summary": obs,
        "checks": all_checks,
        "n_checks": len(all_checks),
        "n_failed": len(failed),
        "failed_checks": failed,
        "verdict": "DIAGNOSIS_CONFIRMED" if not failed else "DIAGNOSIS_DIVERGENCE",
        "control_plane_hardening_items_recorded_not_edited": [
            "The independent-audit job of core-lane.yml runs the same 2700s work quantum as the producer "
            "but must independently recompute a multi-hundred-artifact pack; four consecutive audits have "
            "now starved at the identical boundary. .github/** is control-plane scope and is NOT edited "
            "from this lane. Candidate durable fixes for the control-plane maintainer: raise "
            "LEX_AGENT_QUANTUM_SECONDS for the independent_auditor agent, split the audit into a short "
            "first pass, or hand the auditor a pre-verified pack (this run publishes exactly that).",
            "Job logs remain unauthenticated-readable (403); a durable fix would be a public per-step "
            "duration export or an actions:read token for the auditor. Recorded, not edited.",
        ],
        "non_claims": [
            "No statement about WHY beyond the duration arithmetic is proven from a log line.",
            "This is not a gate verdict: no gate file exists for any of the four runs.",
            "This diagnosis does not decide whether the pending producer work deserves PASS; that is the "
            "independent auditor's decision once the quantum allows it to run.",
        ],
    }


def _resume_dispatch_evidence() -> dict:
    """Durable, git-local evidence that this workspace is the resume of 40204378896.

    The REST run payload does not expose workflow_dispatch inputs, so the resume
    contract is proven the way origin/main implements it: core-lane.yml:80 does
    ``git switch -C operational-resume "origin/$TEAM"`` when resume_from_run_id is
    set (dispatched by the previous run's resilience job at core-lane.yml:385).
    """
    rc_b, branch, _ = git("rev-parse", "--abbrev-ref", "HEAD")
    rc_u, upstream, _ = git("rev-parse", "--abbrev-ref", "@{upstream}")
    rc_a, _, _ = git("merge-base", "--is-ancestor", SNAPSHOT_COMMIT, "HEAD")
    evidence = {
        "branch": branch,
        "upstream": upstream,
        "snapshot_is_ancestor_of_head": rc_a == 0,
        "expected_upstream": f"origin/cycle/core/evaluation/{RESUMED_RUN_ID}/team",
        "workflow_evidence": ["origin/main:.github/workflows/core-lane.yml:80",
                              "origin/main:.github/workflows/core-lane.yml:385"],
    }
    ok = (branch == "operational-resume"
          and upstream == evidence["expected_upstream"]
          and rc_a == 0)
    evidence["ok"] = ok
    return evidence


def build_prior_pack_integrity() -> dict:
    idx_path = PRIOR_PACK / "AUDIT_INDEX_40204378896.json"
    idx = load_json(idx_path)
    rows, bad = [], []
    for entry in idx.get("artifact_inventory", []):
        p = REPO / entry["path"]
        exists = p.is_file()
        digest = sha256_file(p) if exists else None
        ok = exists and digest == entry["sha256"]
        rows.append({"path": entry["path"], "exists": exists,
                     "expected_sha256": entry["sha256"], "observed_sha256": digest,
                     "byte_identical": ok})
        if not ok:
            bad.append(entry["path"])
    rc, head, _ = git("rev-parse", "HEAD")
    frozen = {
        "evaluation/frozen_bars/RULES_LABEL.json": FROZEN_LABEL_SHA,
        "evaluation/frozen_bars/RULES_GEOMETRY.json": FROZEN_GEOMETRY_SHA,
        "results/evaluation/minimal_retrieval_ca_benchmark/40182692670.json": MEASUREMENT_OF_RECORD_SHA,
    }
    frozen_rows = []
    for rel, want in frozen.items():
        p = REPO / rel
        got = sha256_file(p) if p.is_file() else None
        frozen_rows.append({"path": rel, "expected": want, "observed": got, "match": got == want})
        if got != want:
            bad.append(rel)
    gate = REPO / f"results/audit/evaluation/CYCLE_{ACCEPTED_RUN}_GATE.json"
    rc_a, _, _ = git("merge-base", "--is-ancestor", SNAPSHOT_COMMIT, "HEAD")
    rc_b, branch, _ = git("rev-parse", "--abbrev-ref", "HEAD")
    inv_bad = [r["path"] for r in rows if not r["byte_identical"]]

    # every input this run froze BEFORE inspecting outcomes must still hash to
    # the frozen value now; otherwise the run's own freeze is stale.
    freeze = load_json(REPO / f"evaluation/OPERATIONAL_RESUME_{RUN_ID}_FREEZE_V1.json")
    pinned_rows = []
    for rel, want in (freeze.get("frozen_input_hashes") or {}).items():
        p = REPO / rel
        got = sha256_file(p) if p.is_file() else None
        pinned_rows.append({"path": rel, "expected": want, "observed": got, "match": got == want})
        if got != want:
            bad.append(rel)

    checks = [
        check("snapshot_preserved_as_head_or_ancestor",
              head == SNAPSHOT_COMMIT or rc_a == 0,
              head=head, expected_snapshot=SNAPSHOT_COMMIT,
              is_head=head == SNAPSHOT_COMMIT, is_ancestor=rc_a == 0, branch=branch),
        check("prior_pack_inventory_all_byte_identical", not inv_bad,
              n_entries=len(rows), mismatches=inv_bad),
        check("frozen_pins_and_measurement_of_record_unchanged",
              all(r["match"] for r in frozen_rows), rows=frozen_rows),
        check("freeze_pinned_inputs_unchanged",
              all(r["match"] for r in pinned_rows),
              n_pinned=len(pinned_rows),
              mismatches=[r["path"] for r in pinned_rows if not r["match"]],
              note="all 8 inputs hashed by this run's freeze record before any "
                   "outcome was inspected, re-hashed at HEAD"),
        check("accepted_cycle_gate_in_tree", gate.is_file(), gate=str(gate.relative_to(REPO))),
    ]
    failed = [c["check"] for c in checks if not c["passed"]]
    return {
        "schema": "lex-evaluation-operational-resume-prior-pack-integrity/1",
        "run_id": RUN_ID, "pack_under_verification": "40204378896",
        "generated_at_utc": now_utc(),
        "head": head, "expected_snapshot": SNAPSHOT_COMMIT,
        "prior_snapshot": PRIOR_SNAPSHOT_COMMIT,
        "inventory_rows": rows,
        "frozen_rows": frozen_rows,
        "freeze_pinned_rows": pinned_rows,
        "checks": checks, "n_checks": len(checks), "n_failed": len(failed),
        "failed_checks": failed,
        "verdict": "PACK_PRESERVED" if not failed else "PACK_DIVERGENCE",
        "note": ("state/evaluation.json and evaluation/state/evaluation.json are deliberately NOT part "
                 "of the byte-identity set: a resume necessarily advances them. Their prior bytes remain "
                 "readable at commit " + SNAPSHOT_COMMIT + "."),
    }


def build_falsifier_comparison() -> dict:
    """Compare the post-freeze re-execution with the committed measurement of record."""
    committed = load_json(MEASUREMENT_OF_RECORD)
    pre = OUT / "falsifier_replay" / f"{RUN_ID}.json"
    post = OUT / "falsifier_replay_postfreeze" / f"{RUN_ID}.json"
    rows = []
    def cmp(label, a, b, path=""):
        rows.append({"field": label, "equal": a == b,
                     "committed": a if not isinstance(a, (dict, list)) else f"<{type(a).__name__}>",
                     "replay": b if not isinstance(b, (dict, list)) else f"<{type(b).__name__}>"})
    if not post.is_file():
        return {"schema": "lex-evaluation-falsifier-replay-comparison/1", "run_id": RUN_ID,
                "generated_at_utc": now_utc(), "status": "NOT_RUN",
                "record": None, "note": "post-freeze replay record absent; run `verify` first"}
    cur = load_json(post)
    for key in ("verdict", "exit_code", "run_valid", "input_drift", "n_gates", "n_passed",
                "n_failed", "n_reported", "product_mount_head", "frozen_hypothesis",
                "freeze_record", "frozen_label_rubric", "frozen_spec", "rehash_before_execution",
                "rehash_after_execution", "drift_guard", "non_vacuity", "numeric_environment",
                "wrapper_instrument", "engine_entry_point", "engine_invoked_run"):
        cmp(key, committed.get(key), cur.get(key))
    cmp("failed_gate_ids", [g.get("gate") for g in committed.get("failed_gates", [])],
        [g.get("gate") for g in cur.get("failed_gates", [])])
    cmp("gates_payload_byte_equal",
        json.dumps(committed.get("gates"), sort_keys=True),
        json.dumps(cur.get("gates"), sort_keys=True))
    cmp("per_question_byte_equal",
        json.dumps(committed.get("per_question"), sort_keys=True),
        json.dumps(cur.get("per_question"), sort_keys=True))
    unequal = [r["field"] for r in rows if not r["equal"]]
    pre_rows = None
    if pre.is_file():
        p = load_json(pre)
        skip = ("run_id", "generated_at_utc")
        differ = [k for k in sorted(set(p) | set(cur))
                  if k not in skip
                  and json.dumps(p.get(k), sort_keys=True, default=str)
                  != json.dumps(cur.get(k), sort_keys=True, default=str)]
        if not differ:
            expl = ("byte-identical apart from run_id/generated_at_utc: the pre-freeze "
                    "exploratory pass and the recorded post-freeze pass agree exactly")
        elif set(differ) == {"engine_record_path"}:
            expl = ("engine_record_path points at the output directory of the pass it was "
                    "written in (falsifier_replay vs falsifier_replay_postfreeze); it is the "
                    "only field that differs, which is expected because the pre-freeze pass was "
                    "exploratory and ran before the claim artifact was named")
        else:
            expl = ("fields differ beyond the output-directory pointer; inspect "
                    "differing_fields_excluding_run_and_time before trusting REPRODUCES")
        pre_rows = {"exploratory_pre_freeze_present": True,
                    "verdict": p.get("verdict"),
                    "differing_fields_excluding_run_and_time": differ,
                    "differing_fields_explanation": expl,
                    "identical_ignoring_output_directory_pointer":
                        not [k for k in differ if k != "engine_record_path"],
                    "identical_to_recorded_postfreeze": not differ}
    return {
        "schema": "lex-evaluation-falsifier-replay-comparison/1",
        "lane": "evaluation", "run_id": RUN_ID,
        "generated_at_utc": now_utc(),
        "status": "REPRODUCES" if not unequal else "DIVERGENCE",
        "instrument": "python -m evaluation.minimal_retrieval_ca_benchmark -> evaluation.mapping_free_recall_falsifier.run()",
        "committed_measurement_of_record": str(MEASUREMENT_OF_RECORD.relative_to(REPO)),
        "committed_sha256": sha256_file(MEASUREMENT_OF_RECORD),
        "recorded_replay_record": str(post.relative_to(REPO)),
        "replay_sha256": sha256_file(post),
        "fields_compared": len(rows), "fields_equal": len(rows) - len(unequal),
        "unequal_fields": unequal,
        "rows": rows,
        "pre_freeze_exploration": pre_rows,
        "claim_ceiling": ("verification re-execution of an already-frozen protocol in scratch output. "
                          "It is not a second independent falsification, not a re-score of the packet of "
                          "record, and it never overwrites the committed record."),
    }


# --------------------------------------------------------------------- verify
def run_verify() -> int:
    LOGS.mkdir(parents=True, exist_ok=True)
    results, total = [], 0.0
    for key, argv, expect, note in COMMANDS:
        started = time.time()
        pretty = " ".join(argv)
        p = subprocess.run(argv, cwd=str(REPO), capture_output=True, text=True, timeout=1800)
        dur = round(time.time() - started, 3)
        total += dur
        log_path = LOGS / f"{key}_{RUN_ID}.log"
        log_path.write_text(p.stdout + "\n--- stderr ---\n" + p.stderr, encoding="utf-8")
        verdict = None
        m = re.search(r'"verdict":\s*"([^"]+)"', p.stdout)
        if m:
            verdict = m.group(1)
        else:
            m = re.search(r"verdict:\s*(\S+)", p.stdout)
            if m:
                verdict = m.group(1)
            else:
                m = re.search(r"\b(SCOPE_CLEAN|NESTED_REFS_RESOLVED|SHIM_PASS|ALL_CHECKS_PASS)\b", p.stdout)
                verdict = m.group(1) if m else None
        # command-specific pass predicates (frozen in the hypothesis file)
        if key in ("pytest_targeted", "pytest_multilingual_provenance"):
            ok = p.returncode == expect and verdict == "SHIM_PASS"
        elif key == "state_integrity_gate":
            ok = p.returncode == expect and verdict == "ALL_CHECKS_PASS"
        elif key == "nested_evidence_refs_guard":
            ok = p.returncode == expect and verdict == "NESTED_REFS_RESOLVED"
        elif key == "write_scope":
            ok = p.returncode == expect and verdict == "SCOPE_CLEAN"
        elif key == "falsifier_replay_postfreeze":
            ok = p.returncode == 1 and verdict == "PRODUCT_FALSIFIED"
        else:
            ok = p.returncode == expect
        results.append({
            "key": key, "command": pretty, "argv": argv,
            "expected_exit_code": expect, "exit_code": p.returncode,
            "wall_seconds": dur, "verdict": verdict, "passed": ok,
            "note": note, "log": str(log_path.relative_to(REPO)),
        })
    record = {
        "schema": "lex-evaluation-operational-resume-command-runtimes/1",
        "lane": "evaluation", "run_id": RUN_ID, "generated_at_utc": now_utc(),
        "results": results,
        "n_commands": len(results),
        "n_passed": sum(1 for r in results if r["passed"]),
        "n_failed": sum(1 for r in results if not r["passed"]),
        "total_measured_seconds": round(total, 3),
        "total_measured_seconds_human": f"{total/60:.1f} min",
        "audit_budget_seconds": 2700,
        "pack_reexecution_fits_in_audit_quantum": total < 2700,
        "all_commands_exit_zero_except_expected": all(
            r["exit_code"] == r["expected_exit_code"] for r in results),
        "verdict": "COMMANDS_PASS" if all(r["passed"] for r in results) else "COMMANDS_FAIL",
    }
    out = OUT / f"command_runtimes_{RUN_ID}.json"
    sha = write_json(out, record)
    print(json.dumps({"verdict": record["verdict"], "n_passed": record["n_passed"],
                      "n_failed": record["n_failed"],
                      "total_measured_seconds": record["total_measured_seconds"],
                      "record": str(out.relative_to(REPO)), "sha256": sha}, indent=2))
    return 0 if record["verdict"] == "COMMANDS_PASS" else 1


def prepare() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    diag = build_diagnosis(capture=False)
    d_sha = write_json(OUT / f"diagnosis_{RESUMED_RUN_ID}.json", diag)
    integ = build_prior_pack_integrity()
    i_sha = write_json(OUT / f"prior_pack_integrity_{RUN_ID}.json", integ)
    comp = build_falsifier_comparison()
    c_sha = write_json(OUT / f"falsifier_replay_comparison_{RUN_ID}.json", comp)
    summary = {
        "diagnosis": {"verdict": diag["verdict"], "n_checks": diag["n_checks"],
                      "n_failed": diag["n_failed"], "sha256": d_sha,
                      "failure_class": diag["failure_class"],
                      "duration_seconds": diag["observation_summary"]["duration_value"]},
        "prior_pack_integrity": {"verdict": integ["verdict"], "n_checks": integ["n_checks"],
                                 "n_failed": integ["n_failed"], "sha256": i_sha},
        "falsifier_replay_comparison": {"status": comp["status"], "sha256": c_sha,
                                        "fields_compared": comp.get("fields_compared"),
                                        "fields_equal": comp.get("fields_equal")},
    }
    ok = (diag["verdict"] == "DIAGNOSIS_CONFIRMED"
          and integ["verdict"] == "PACK_PRESERVED"
          and comp["status"] in ("REPRODUCES", "NOT_RUN"))
    print(json.dumps({**summary, "prepare_exit": 0 if ok else 1}, indent=2))
    return 0 if ok else 1


def finalize() -> int:
    """Hash-indexed audit pack; refuses audit-ready if any record/hash/posture check fails."""
    state = load_json(REPO / "state/evaluation.json")
    lane_state = load_json(REPO / "evaluation/state/evaluation.json")
    runtimes = load_json(OUT / f"command_runtimes_{RUN_ID}.json") if (
        OUT / f"command_runtimes_{RUN_ID}.json").is_file() else None
    required = [
        OUT / f"diagnosis_{RESUMED_RUN_ID}.json",
        OUT / f"prior_pack_integrity_{RUN_ID}.json",
        OUT / f"falsifier_replay_comparison_{RUN_ID}.json",
        OUT / f"state_integrity_gate_{RUN_ID}.json",
        OUT / f"write_scope_{RUN_ID}.json",
        OUT / f"pytest_targeted_{RUN_ID}.json",
        OUT / f"pytest_multilingual_provenance_{RUN_ID}.json",
        HYPOTHESIS, FREEZE,
    ]
    checks = []
    for p in required:
        checks.append(check(f"exists:{p.relative_to(REPO)}", p.is_file()))
    diag = load_json(OUT / f"diagnosis_{RESUMED_RUN_ID}.json")
    integ = load_json(OUT / f"prior_pack_integrity_{RUN_ID}.json")
    comp = load_json(OUT / f"falsifier_replay_comparison_{RUN_ID}.json")
    sig = load_json(OUT / f"state_integrity_gate_{RUN_ID}.json")
    checks.append(check("diagnosis_confirmed", diag.get("verdict") == "DIAGNOSIS_CONFIRMED"))
    checks.append(check("prior_pack_preserved", integ.get("verdict") == "PACK_PRESERVED"))
    checks.append(check("falsifier_reproduces", comp.get("status") == "REPRODUCES"))
    checks.append(check("state_integrity_all_checks_pass",
                        sig.get("verdict") == "ALL_CHECKS_PASS"))
    if runtimes:
        checks.append(check("commands_pass", runtimes.get("verdict") == "COMMANDS_PASS"))
        checks.append(check("pack_reexecution_under_quantum",
                            runtimes.get("pack_reexecution_fits_in_audit_quantum") is True,
                            total_seconds=runtimes.get("total_measured_seconds")))
    posture = [
        check("accepted_run_id_unchanged", state.get("accepted_run_id") == ACCEPTED_RUN,
              value=state.get("accepted_run_id")),
        check("direction_version_68", state.get("direction_version") == DIRECTION_VERSION
              == lane_state.get("direction_version")),
        check("github_run_parity", state.get("github_run") == lane_state.get("github_run")
              == int(RUN_ID)),
        check("continue_recommended_false", state.get("continue_recommended") is False),
        check("human_gate_ready_false", state.get("human_gate_ready") is False),
        check("machine_gate_ready_false", state.get("machine_gate_ready") is False),
        check("evidence_refs_n_root", state.get("evidence_refs_n") == len(state.get("evidence_refs", []))),
        check("evidence_refs_n_lane", lane_state.get("evidence_refs_n") == len(lane_state.get("evidence_refs", []))),
        check("item_2_still_not_yet_discriminating",
              state.get("v68_item_2_reconciliation_40192868113", {}).get("current_item_2_status")
              == "NOT_YET_DISCRIMINATING"),
    ]
    checks.extend(posture)
    failed = [c["check"] for c in checks if not c["passed"]]
    status = "AUDIT_READY_PENDING_INDEPENDENT_AUDIT" if not failed else "DIVERGENCE"

    # summary is written first so the index can inventory it (same run, same
    # namespace: this file is regenerated by every `finalize` of THIS run and is
    # not a historical artifact of any other run).
    summary = {
        "schema": "lex-evaluation-operational-resume-summary/1",
        "lane": "evaluation", "run_id": RUN_ID,
        "resumed_run_id": RESUMED_RUN_ID, "direction_version": DIRECTION_VERSION,
        "generated_at_utc": now_utc(),
        "status": status,
        "failure_class": diag.get("failure_class"),
        "diagnosis_verdict": diag.get("verdict"),
        "prior_pack_verdict": integ.get("verdict"),
        "falsifier_replay_status": comp.get("status"),
        "state_integrity_verdict": sig.get("verdict"),
        "command_runtimes": ({k: runtimes.get(k) for k in
                              ("verdict", "n_commands", "n_passed", "n_failed",
                               "total_measured_seconds", "total_measured_seconds_human",
                               "pack_reexecution_fits_in_audit_quantum")}
                             if runtimes else None),
        "posture": {k: state.get(k) for k in
                    ("accepted_run_id", "direction_version", "github_run",
                     "continue_recommended", "human_gate_ready", "machine_gate_ready",
                     "evidence_tier", "cycle_status")},
        "checks": checks,
        "n_checks": len(checks), "n_failed": len(failed), "failed_checks": failed,
        "claim_ceiling": ("Operational-resume verification only. No frozen bar, rubric, threshold, "
                          "serve verdict, admission flag, DO-NOT-SERVE change, new same-question cycle "
                          "or 174k rerun. This is the producer's own record and is NOT an independent "
                          "audit; no gate file is created by this run."),
    }
    write_json(OUT / f"summary_{RUN_ID}.json", summary)

    inventory = []
    for p in sorted(OUT.rglob("*")):
        if p.is_file() and p.name not in (f"AUDIT_INDEX_{RUN_ID}.json",):
            inventory.append({"path": str(p.relative_to(REPO)), "sha256": sha256_file(p),
                              "bytes": p.stat().st_size})
    for p in (HYPOTHESIS, FREEZE, REPORT):
        if p.is_file():
            inventory.append({"path": str(p.relative_to(REPO)), "sha256": sha256_file(p),
                              "bytes": p.stat().st_size})

    index = {
        "schema": "lex-evaluation-operational-resume-audit-index/1",
        "lane": "evaluation", "run_id": RUN_ID,
        "resumed_run_id": RESUMED_RUN_ID,
        "direction_version": DIRECTION_VERSION,
        "generated_at_utc": now_utc(),
        "purpose": ("One-page, hash-indexed map from each claim to its committed artifact and the exact "
                    "executable check that re-derives it, with the measured wall time of that check. It is "
                    "the compact audit entry point for the independent auditor; it does not replace "
                    "independent recomputation."),
        "claim_to_artifact": {
            "orchestration_failure_is_quantum_not_producer": [
                f"results/evaluation/operational_resume_40209360877/diagnosis_{RESUMED_RUN_ID}.json",
                f"results/evaluation/operational_resume_40209360877/api/jobs_{RESUMED_RUN_ID}_api.json",
                f"results/evaluation/operational_resume_40209360877/api/run_{RESUMED_RUN_ID}_api.json",
                "results/evaluation/operational_resume_40209360877/api/jobs_40198184759_api.json",
                "results/evaluation/operational_resume_40209360877/api/jobs_40192868113_api.json",
                "results/evaluation/operational_resume_40209360877/api/jobs_40187594111_api.json",
            ],
            "prior_audit_ready_pack_preserved": [
                f"results/evaluation/operational_resume_40209360877/prior_pack_integrity_{RUN_ID}.json",
                "results/evaluation/operational_resume_40204378896/AUDIT_INDEX_40204378896.json",
                "reports/evaluation/OPERATIONAL_RESUME_40204378896_AUDIT_READY.md",
            ],
            "smallest_retrieval_ca_falsifier_still_reproduces": [
                f"results/evaluation/operational_resume_40209360877/falsifier_replay_comparison_{RUN_ID}.json",
                f"results/evaluation/operational_resume_40209360877/falsifier_replay_postfreeze/{RUN_ID}.json",
                "results/evaluation/minimal_retrieval_ca_benchmark/40182692670.json",
                "evaluation/MAPPING_FREE_RECALL_FALSIFIER_HYPOTHESIS_V1.json",
                "evaluation/MAPPING_FREE_RECALL_FALSIFIER_FREEZE_RECORD.json",
            ],
            "state_and_scope_consistent": [
                f"results/evaluation/operational_resume_40209360877/state_integrity_gate_{RUN_ID}.json",
                f"results/evaluation/operational_resume_40209360877/nested_refs/{RUN_ID}_nested_evidence_refs.json",
                f"results/evaluation/operational_resume_40209360877/write_scope_{RUN_ID}.json",
                f"results/evaluation/operational_resume_40209360877/pytest_targeted_{RUN_ID}.json",
                f"results/evaluation/operational_resume_40209360877/pytest_multilingual_provenance_{RUN_ID}.json",
            ],
            "posture_unchanged": [
                "state/evaluation.json",
                "evaluation/state/evaluation.json",
                f"results/evaluation/operational_resume_40209360877/summary_{RUN_ID}.json",
            ],
        },
        "exact_commands": [
            {"key": r["key"], "command": r["command"], "expected_exit_code": r["expected_exit_code"],
             "measured_seconds": r["wall_seconds"], "verdict": r["verdict"], "passed": r["passed"]}
            for r in (runtimes or {}).get("results", [])
        ],
        "total_measured_seconds": (runtimes or {}).get("total_measured_seconds"),
        "audit_budget_seconds": 2700,
        "auditor_shortcut": (
            "Run `python3 evaluation/operational_resume_40209360877.py verify && "
            "python3 evaluation/operational_resume_40209360877.py prepare && "
            "python3 evaluation/operational_resume_40209360877.py finalize` in the producer worktree "
            "(/tmp/lex_team during an audit). `verify` re-runs every pre-registered command with measured "
            "wall time and refuses to print AUDIT_READY if any check, hash or posture assertion fails."),
        "artifact_inventory": sorted(inventory, key=lambda r: r["path"]),
        "checks": checks,
        "n_checks": len(checks),
        "n_failed": len(failed),
        "failed_checks": failed,
        "status": "AUDIT_READY_PENDING_INDEPENDENT_AUDIT" if not failed else "DIVERGENCE",
        "claim_ceiling": (
            "Operational-resume verification only. It preserves the accepted evaluation cycle "
            f"{ACCEPTED_RUN} and the {RESUMED_RUN_ID} audit-ready pack byte-for-byte, keeps item (2) "
            "NOT_YET_DISCRIMINATING, re-executes the already-frozen smallest retrieval/counter-authority "
            "falsifier in scratch (PRODUCT_FALSIFIED unchanged), moves no frozen bar, issues no serve "
            "verdict, lifts no DO-NOT-SERVE order, opens no new same-question cycle and runs no 174k "
            "benchmark. It is not an independent audit and does not create a gate."),
    }
    sha = write_json(OUT / f"AUDIT_INDEX_{RUN_ID}.json", index)
    print(json.dumps({"status": index["status"], "n_checks": index["n_checks"],
                      "n_failed": index["n_failed"], "failed_checks": failed,
                      "total_measured_seconds": index["total_measured_seconds"],
                      "record": f"results/evaluation/operational_resume_{RUN_ID}/AUDIT_INDEX_{RUN_ID}.json",
                      "sha256": sha}, indent=2))
    return 0 if not failed else 1


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    mode = argv[0] if argv else "prepare"
    if mode == "verify":
        return run_verify()
    if mode == "prepare":
        return prepare()
    if mode == "finalize":
        return finalize()
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
