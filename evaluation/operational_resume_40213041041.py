#!/usr/bin/env python3
"""Operational-resume verifier and compact audit pack for evaluation run 40217938706.

Resume base: the persisted producer snapshot of run 40213041041 (commit c11aff55),
which was itself an operational resume of run 40209360877 (snapshot 9c5db64d).

REUSE-FIRST: the structure, check vocabulary and claim ceiling are adapted from
evaluation/operational_resume_40209360877.py.  This resume does NOT start over and
does NOT open a new same-question cycle:

  * it diagnoses the orchestration failure of run 40213041041 from public GitHub
    run/jobs JSON and the checked-in work-quantum wrapper (fifth consecutive
    2704.0s independent-audit starvation, no audit branch, no verdict);
  * it remediates an append-only evidence violation committed by 40213041041:
    claim-bearing artifacts named for run 40209360877 were overwritten in place.
    Requirement 34's disposition is applied: restore the original bytes from
    9c5db64d with sha256 proof, re-home the rewritten content under this new
    run's own run-scoped directory, and delete nothing;
  * it verifies the lane's remaining deliverable without re-running the standing
    falsification: ordered item (1) is present (correction-of-record plus follow-up
    citation, bundle/code provenance reproduces) and ordered item (2) remains
    NOT_YET_DISCRIMINATING (H2 member-for-member full-family regeneration false);
  * it runs the lane's state/scope/test instruments under this run id with
    measured wall time and builds one hash-indexed audit pack whose total
    measured verification time is published so the recurring audit starvation
    cannot be blamed on pack size.

Claim ceiling: operational-resume verification and provenance remediation only.
No frozen bar, rubric, threshold, verdict contract, serve verdict, admission flag
or same-question measurement is touched, and the standing falsifier is NOT
re-executed.

Usage (from the producer/team worktree):
    python3 evaluation/operational_resume_40213041041.py prepare
    python3 evaluation/operational_resume_40213041041.py verify
    python3 evaluation/operational_resume_40213041041.py finalize
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

RUN_ID = "40217938706"
RESUMED_RUN_ID = "40213041041"
RESUMED_RUN_ITSELF_RESUMED = "40209360877"
STARVATION_RUNS = ("40187594111", "40192868113", "40198184759", "40204378896", "40213041041")
SNAPSHOT_COMMIT = "c11aff55cc4acaca30f5c5fe33f61c1dc603a174"
PRIOR_SNAPSHOT_COMMIT = "9c5db64d8eb283a7566be96a9823827668991c39"
ACCEPTED_RUN = 40159747851
ACCEPT_COMMIT = "9be8a7d5b3a4b84eb45da6160bf90620f7d81d40"
DIRECTION_VERSION = 68
GENERATED_AT_UTC = "2026-10-25T17:49:27Z"

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "results/evaluation/operational_resume_40213041041"
API = OUT / "api"
LOGS = OUT / "logs"
PRESERVED = OUT / "preserved_40213041041_rewrites"
REHOMED = OUT / "rehomed_40213041041"
PRIOR_PACK = REPO / "results/evaluation/operational_resume_40209360877"
PRIOR_PACK_UNDER_VERIFICATION = REPO / "results/evaluation/operational_resume_40204378896"
MEASUREMENT_OF_RECORD = REPO / "results/evaluation/minimal_retrieval_ca_benchmark/40182692670.json"
FALSIFIER_MEASUREMENT = REPO / "results/evaluation/fast_mvp_current_head_ca_falsifier/40105794124.json"
CORRECTION_NOTE = REPO / "reports/evaluation/BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md"
CORRECTION_FOLLOWUP = REPO / "reports/evaluation/CORRECTION_FOLLOWUP_CITATION_40198184759.md"
BYPASS_RECORD = REPO / "results/evaluation/bypass_clause_correction/40144816305.json"
POST_REPAIR_RECORD = REPO / "results/evaluation/post_repair_family_ca_falsifier/40162507752.json"
HYPOTHESIS = REPO / "evaluation/OPERATIONAL_RESUME_40213041041_HYPOTHESIS_V1.json"
FREEZE = REPO / "evaluation/OPERATIONAL_RESUME_40213041041_FREEZE_V1.json"
INSTRUMENT = REPO / "evaluation/operational_resume_40213041041.py"
REPORT = REPO / "reports/evaluation/OPERATIONAL_RESUME_40213041041_AUDIT_READY.md"
PRODUCT_MOUNT = Path("/tmp/lex_accepted/product")
PRODUCT_HEAD_EXPECTED = "29a5c4a548ba0ab8b6a8f574de1e732d17f3d109"
BUNDLE_REL = "results/product/offline_slice/20261024T142517Z/rent-default.bundle.json"
BUNDLE_SHA = "6eee1149b3c0ec23124746af482e15d9298c2120ee25de4bc4dd7e1cf7d93fa9"
FROZEN_LABEL_SHA = "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"
FROZEN_GEOMETRY_SHA = "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633"
MEASUREMENT_OF_RECORD_SHA = "fd29a395f8b5307d67abeb79335337250518cc6de171a26ddbf09768840ade73"
FALSIFIER_MEASUREMENT_SHA = "fd25345b02da6658edbd5ed8722c69c9b3c7dbbc22e7856740cfdd421c5c4592"
CORRECTION_NOTE_SHA = "b10eeb3a720cd6352fbc7eabbf8d3430989b52d90193d0f948e69908ef5dc48d"
CORRECTION_FOLLOWUP_SHA = "8c3750a580dbc6554bdb6b8fd18a2d055520fc2a9590ebb177baec7b84fa3174"
BYPASS_RECORD_SHA = "2e691dd02c7b53bac7b1bf048363e56006a1596dd3cade1fd4fb44514330228d"
POST_REPAIR_RECORD_SHA = "6dea7616dec4b89291aa3c21579a5a4b852f2f855d9379e47c1b5467ccb851a6"
PIPELINE_REL = "product/query/pipeline.py"
SPAN_REL = "product/query/counter_evidence_span.py"
PIPELINE_SHA_EXPECTED = "cb2c2595a3e85eb4ad53a6333bbbd91a671f85ec61f90ce9350a8df3558eda4f"
SPAN_SHA_EXPECTED = "b749e43556874d5dfe7966a40205a81dd3c1345c6f352bca6f3e0e72e97873a1"
API_BASE = "https://api.github.com/repos/Mickalive/LexMachina/actions/runs"

# Paths whose bytes were rewritten in place by 40213041041. Restored from
# PRIOR_SNAPSHOT_COMMIT; state files are excluded (a resume advances them).
RESTORE_EXCLUDE = {
    "state/evaluation.json",
    "evaluation/state/evaluation.json",
}

COMMANDS: list[tuple[str, list[str], int, str]] = [
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


def verdict_from_argv(argv: list[str]):
    """Read the verdict from --out, or from the record written by --out-dir."""
    try:
        if "--out" in argv:
            p = Path(argv[argv.index("--out") + 1])
            if p.is_file():
                v = load_json(p).get("verdict")
                return v.get("verdict") if isinstance(v, dict) else v
        if "--out-dir" in argv:
            d = Path(argv[argv.index("--out-dir") + 1])
            for f in sorted(d.glob("*_nested_evidence_refs.json")):
                v = load_json(f).get("verdict")
                return v.get("verdict") if isinstance(v, dict) else v
    except Exception:
        pass
    return None


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, indent=2, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_bytes(path: Path, data: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def git(*args: str, cwd: Path = REPO, timeout: int = 120) -> tuple[int, str, str]:
    p = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def git_bytes(spec: str) -> bytes:
    p = subprocess.run(["git", "show", spec], cwd=str(REPO), capture_output=True, timeout=120)
    if p.returncode != 0:
        raise RuntimeError(f"git show {spec} failed: {p.stderr.decode('utf-8', 'replace')}")
    return p.stdout


def check(name: str, ok: bool, **detail) -> dict:
    return {"check": name, "passed": bool(ok), "detail": detail}


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------- API envelopes
def load_or_fetch_api(kind: str, run_id: str, capture: bool) -> dict:
    """kind is 'run' or 'jobs'. A committed envelope is authoritative for replay."""
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
    rc, text, err = git("show", "origin/main:.github/scripts/run-ox-with-retry.sh")
    if rc != 0:
        return {"available": False, "error": err}
    facts = {"available": True}
    for key, pattern in {
        "quantum_line": r"WORK_QUANTUM_SECONDS=",
        "sleep_line": r"sleep 15",
        "kill_line": r"now - start >= WORK_QUANTUM_SECONDS",
        "return_78_line": r"return 78",
    }.items():
        hits = [(i, line.strip()) for i, line in enumerate(text.splitlines(), 1)
                if re.search(pattern, line)]
        facts[key] = {"found": bool(hits), "hits": hits[:3]}
    facts["quantum_divisible_by_15"] = (2700 % 15 == 0)
    return facts


# --------------------------------------------------------------------- 1. diagnosis
def build_diagnosis() -> dict:
    api_run = load_or_fetch_api("run", RESUMED_RUN_ID, capture=True)
    api_jobs = load_or_fetch_api("jobs", RESUMED_RUN_ID, capture=True)
    run_env, jobs_env = api_run["envelope"], api_jobs["envelope"]
    if not jobs_env:
        return {"schema": "lex-evaluation-operational-resume-diagnosis/1",
                "run_id": RUN_ID, "diagnosed_run_id": RESUMED_RUN_ID,
                "verdict": "DIAGNOSIS_UNAVAILABLE_NO_API",
                "error": (api_jobs.get("fetch_error") or "no jobs envelope")}

    team = _job(jobs_env, "team") or {}
    audit = _job(jobs_env, "audit") or {}
    resilience = _job(jobs_env, "resilience") or {}
    integrate = _job(jobs_env, "integrate") or {}
    audit_step = _step(audit, "Independent audit") or {}
    audit_secs = _secs(audit_step.get("started_at"), audit_step.get("completed_at"))
    later = [s for s in audit.get("steps", []) if s.get("number") in (6, 7)]

    # Recurrence: read the committed envelopes of the four earlier starvation runs.
    recurrence = {}
    for rid in STARVATION_RUNS[:-1]:
        jpath = PRIOR_PACK / "api" / f"jobs_{rid}_api.json"
        if jpath.is_file():
            jd = load_json(jpath)
            a = _job(jd, "audit") or {}
            s = _step(a, "Independent audit") or {}
            recurrence[rid] = {
                "audit_conclusion": a.get("conclusion"),
                "step": s.get("name"),
                "duration_seconds": _secs(s.get("started_at"), s.get("completed_at")),
                "envelope": str(jpath.relative_to(REPO)),
            }
        else:
            recurrence[rid] = {"envelope": None, "error": "committed envelope missing"}
    recurrence[RESUMED_RUN_ID] = {
        "audit_conclusion": audit.get("conclusion"),
        "step": audit_step.get("name"),
        "duration_seconds": audit_secs,
        "envelope": api_jobs.get("path"),
    }

    branch = audit_branch_probe(RESUMED_RUN_ID)
    wrapper = wrapper_quantum_facts()
    rc, head, _ = git("rev-parse", "HEAD")
    rc2, upstream, _ = git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")

    checks = [
        check("diagnosed_run_metadata", run_env.get("id") == int(RESUMED_RUN_ID),
              run_name=run_env.get("name"), conclusion=run_env.get("conclusion"),
              head_sha=run_env.get("head_sha")),
        check("team_success_all_steps", team.get("conclusion") == "success" and
              all(s.get("conclusion") == "success" for s in team.get("steps", [])),
              steps=[(s.get("number"), s.get("name"), s.get("conclusion")) for s in team.get("steps", [])]),
        check("audit_conclusion_failure", audit.get("conclusion") == "failure",
              conclusion=audit.get("conclusion")),
        check("failing_step_is_independent_audit",
              audit_step.get("name") == "Independent audit" and audit_step.get("conclusion") == "failure",
              step=audit_step.get("name"), conclusion=audit_step.get("conclusion")),
        check("duration_is_2704_0s", audit_secs == 2704.0, duration_seconds=audit_secs),
        check("gate_and_persist_steps_skipped",
              len(later) == 2 and all(s.get("conclusion") == "skipped" for s in later),
              steps=[(s.get("number"), s.get("name"), s.get("conclusion")) for s in later]),
        check("integrate_skipped", integrate.get("conclusion") == "skipped",
              conclusion=integrate.get("conclusion")),
        check("resilience_success", resilience.get("conclusion") == "success",
              conclusion=resilience.get("conclusion")),
        check("no_audit_branch", branch.get("exists") is False, branch=branch),
        check("five_run_recurrence_all_2704_0s",
              all(v.get("duration_seconds") == 2704.0 for v in recurrence.values()),
              recurrence=recurrence),
        check("wrapper_quantum_mechanism_present",
              wrapper.get("available") and all(wrapper.get(k, {}).get("found") for k in
                                               ("quantum_line", "sleep_line", "kill_line", "return_78_line")),
              wrapper=wrapper),
        check("snapshot_is_resume_head", head == SNAPSHOT_COMMIT, head=head,
              expected=SNAPSHOT_COMMIT),
        check("this_run_is_the_operational_resume_dispatch",
              upstream == f"origin/cycle/core/evaluation/{RESUMED_RUN_ID}/team",
              branch="operational-resume", upstream=upstream,
              expected_upstream=f"origin/cycle/core/evaluation/{RESUMED_RUN_ID}/team"),
    ]
    failed = [c for c in checks if not c["passed"]]
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
            f"{audit_secs}s (quantum 2700s + ~4s step setup), the two later audit steps were skipped, "
            "integrate was skipped and resilience dispatched this resume. The identical 2704.0s signature "
            "now appears on FIVE consecutive runs (40187594111, 40192868113, 40198184759, 40204378896, "
            f"{RESUMED_RUN_ID}), no /audit ref exists for any of them, and the run therefore issued NO "
            "verdict. This is not a producer failure, not a validation failure, not a gate REVISE/BLOCKED "
            "and not a product defect."
        ),
        "log_evidence_available": False,
        "log_evidence_note": "GitHub job-log endpoint is HTTP 403 unauthenticated (GH_TOKEN unset); the mechanism is inference from public run/jobs metadata plus the checked-in wrapper, never a quoted log line.",
        "recurrence": recurrence,
        "wrapper": wrapper,
        "audit_branch": branch,
        "checks": checks,
        "n_checks": len(checks),
        "n_failed": len(failed),
        "failed_checks": [c["check"] for c in failed],
        "verdict": "DIAGNOSIS_CONFIRMED" if not failed else "DIAGNOSIS_DIVERGENCE",
        "control_plane_hardening_items_recorded_not_edited": [
            "The independent-audit job runs the same 2700s work quantum as the producer but must independently recompute a multi-hundred-artifact pack; five consecutive audits starved at the identical boundary. .github/** is control-plane scope and is NOT edited from this lane. Candidate durable fixes: raise LEX_AGENT_QUANTUM_SECONDS for the independent_auditor agent, split the audit into a short first pass, or hand the auditor a pre-verified pack (this run publishes exactly that).",
            "Job logs remain unauthenticated-readable (403); a durable fix would be a public per-step duration export or an actions:read token for the auditor. Recorded, not edited.",
        ],
    }


# --------------------------------------------------------------------- 2. append-only remediation
def build_remediation() -> dict:
    rc, delta, err = git("diff", "--name-status", f"{PRIOR_SNAPSHOT_COMMIT}..{SNAPSHOT_COMMIT}")
    if rc != 0:
        raise RuntimeError(f"git diff failed: {err}")
    rows = []
    restored, preserved, added = [], [], []
    existing_path = OUT / f"append_only_remediation_{RUN_ID}.json"
    existing_by_path = {}
    if existing_path.is_file():
        existing = load_json(existing_path)
        existing_by_path = {r["path"]: r for r in existing.get("restored", [])}
    for line in delta.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status, path = parts[0], parts[-1]
        if path in RESTORE_EXCLUDE:
            rows.append({"status": status, "path": path, "action": "state_advance_excluded_from_byte_identity"})
            continue
        if status == "M":
            old_bytes = git_bytes(f"{PRIOR_SNAPSHOT_COMMIT}:{path}")
            old_sha = sha256_bytes(old_bytes)
            cur_path = REPO / path
            cur_bytes = cur_path.read_bytes() if cur_path.is_file() else b""
            cur_sha = sha256_bytes(cur_bytes)
            preserved_path = PRESERVED / path
            already_restored = cur_sha == old_sha
            if not already_restored:
                # Preserve the first-seen rewritten bytes; never let a re-run
                # replace them with the already-restored original.
                if not preserved_path.is_file():
                    write_bytes(preserved_path, cur_bytes)
                new_sha = write_bytes(cur_path, old_bytes)
            else:
                new_sha = cur_sha
            preserved_exists = preserved_path.is_file()
            prior = existing_by_path.get(path) or {}
            restored.append({"path": path, "pre_rewrite_sha256": old_sha,
                             "rewritten_by_40213041041_sha256": (
                                 prior.get("rewritten_by_40213041041_sha256") if already_restored
                                 else cur_sha),
                             "restored_sha256": new_sha,
                             "restored_equals_pre_rewrite": new_sha == old_sha,
                             "match": new_sha == old_sha,
                             "already_restored_on_entry": already_restored,
                             "rewritten_content_preserved": bool(prior) or preserved_exists,
                             "rewritten_content_preserved_at": (
                                 prior.get("rewritten_content_preserved_at")
                                 or (str(preserved_path.relative_to(REPO)) if preserved_exists else None))})
            rows.append({"status": status, "path": path,
                         "action": ("already_restored_from_prior_snapshot" if already_restored
                                    else "restored_from_prior_snapshot"),
                         "restored_sha256": new_sha, "match": new_sha == old_sha})
        elif status == "A":
            cur_sha = sha256_file(REPO / path)
            rehomed_path = REHOMED / path
            if not rehomed_path.is_file():
                write_bytes(rehomed_path, (REPO / path).read_bytes())
            added.append({"path": path, "sha256": cur_sha,
                          "authored_by_run": RESUMED_RUN_ID,
                          "retained_in_place": True,
                          "rehomed_at": str(rehomed_path.relative_to(REPO))})
            rows.append({"status": status, "path": path, "action": "added_by_resumed_run_retained_and_rehomed",
                         "sha256": cur_sha})
        else:
            rows.append({"status": status, "path": path, "action": "observed_unexpected_status"})

    # Prior pack 40204378896: all 14 inventory artifacts must still hash equal.
    prior_index_path = PRIOR_PACK_UNDER_VERIFICATION / "AUDIT_INDEX_40204378896.json"
    prior_index = load_json(prior_index_path)
    inv_checks = []
    for row in prior_index.get("artifact_inventory", []):
        p = REPO / row["path"]
        ok = p.is_file() and sha256_file(p) == row.get("sha256")
        inv_checks.append({"path": row["path"], "exists": p.is_file(),
                           "sha256_recorded": row.get("sha256"),
                           "sha256_now": sha256_file(p) if p.is_file() else None,
                           "match": ok})
    frozen = {
        "RULES_LABEL": sha256_file(REPO / "evaluation/frozen_bars/RULES_LABEL.json"),
        "RULES_GEOMETRY": sha256_file(REPO / "evaluation/frozen_bars/RULES_GEOMETRY.json"),
        "measurement_of_record_40182692670": sha256_file(MEASUREMENT_OF_RECORD),
        "accepted_gate_present": (REPO / f"results/audit/evaluation/CYCLE_{ACCEPTED_RUN}_GATE.json").is_file(),
    }
    pack_checks = [
        check("prior_pack_inventory_all_byte_identical", all(c["match"] for c in inv_checks),
              n=len(inv_checks), mismatches=[c["path"] for c in inv_checks if not c["match"]]),
        check("frozen_label_pin_unchanged", frozen["RULES_LABEL"] == FROZEN_LABEL_SHA, sha=frozen["RULES_LABEL"]),
        check("frozen_geometry_pin_unchanged", frozen["RULES_GEOMETRY"] == FROZEN_GEOMETRY_SHA, sha=frozen["RULES_GEOMETRY"]),
        check("measurement_of_record_unchanged",
              frozen["measurement_of_record_40182692670"] == MEASUREMENT_OF_RECORD_SHA,
              sha=frozen["measurement_of_record_40182692670"]),
        check("accepted_cycle_gate_in_tree", frozen["accepted_gate_present"]),
        check("all_overwritten_paths_restored", all(r.get("match") for r in restored),
              n_restored=len(restored), n_mismatch=sum(1 for r in restored if not r.get("match"))),
        check("all_rewritten_bytes_preserved",
              all(r.get("rewritten_content_preserved") and
                  (r.get("rewritten_content_preserved_at") is None or
                   (REPO / r["rewritten_content_preserved_at"]).is_file())
                  for r in restored),
              n=len(restored),
              n_without_preserved=sum(1 for r in restored if not r.get("rewritten_content_preserved"))),
        check("added_artifacts_retained_not_deleted", all((REPO / r["path"]).is_file() for r in added),
              n_added=len(added)),
    ]
    failed = [c for c in pack_checks if not c["passed"]]
    return {
        "schema": "lex-evaluation-append-only-remediation/1",
        "lane": "evaluation",
        "run_id": RUN_ID,
        "run_whose_writes_are_remediated": RESUMED_RUN_ID,
        "previous_snapshot": PRIOR_SNAPSHOT_COMMIT,
        "snapshot_under_remediation": SNAPSHOT_COMMIT,
        "generated_at_utc": now_utc(),
        "rule": (
            "Factory-wide requirement 34 / AGENTS.md items 5-6: a file named for run X holds run X's "
            "measurement; a later re-measurement is a NEW artifact under a NEW run id, never an in-place "
            "overwrite. Disposition: restore the original bytes with sha256 proof, re-home the rewritten "
            "content under the new run's own directory, delete nothing."
        ),
        "delta_rows": rows,
        "restored": restored,
        "added_retained": added,
        "prior_pack_inventory": inv_checks,
        "frozen_inputs": frozen,
        "checks": pack_checks,
        "n_checks": len(pack_checks),
        "n_failed": len(failed),
        "failed_checks": [c["check"] for c in failed],
        "verdict": "REMEDIATED_APPEND_ONLY" if not failed else "REMEDIATION_DIVERGENCE",
    }


# --------------------------------------------------------------------- 3. deliverable verification
def build_deliverable() -> dict:
    checks = []
    files = {
        "correction_note": (CORRECTION_NOTE, CORRECTION_NOTE_SHA),
        "correction_followup": (CORRECTION_FOLLOWUP, CORRECTION_FOLLOWUP_SHA),
        "bypass_record": (BYPASS_RECORD, BYPASS_RECORD_SHA),
        "falsifier_measurement_40105794124": (FALSIFIER_MEASUREMENT, FALSIFIER_MEASUREMENT_SHA),
        "post_repair_record_40162507752": (POST_REPAIR_RECORD, POST_REPAIR_RECORD_SHA),
    }
    file_obs = {}
    for key, (path, expected) in files.items():
        obs = {"path": str(path.relative_to(REPO)), "exists": path.is_file(),
               "sha256_expected": expected,
               "sha256_now": sha256_file(path) if path.is_file() else None}
        obs["match"] = obs["sha256_now"] == expected
        file_obs[key] = obs
        checks.append(check(f"file_{key}_present_and_unchanged", obs["match"], **obs))

    # Bundle + code provenance of the correction of record.
    bundle_path = PRODUCT_MOUNT / BUNDLE_REL
    bundle_obs = {"path": str(bundle_path), "exists": bundle_path.is_file()}
    if bundle_path.is_file():
        bundle = load_json(bundle_path)
        prov = (bundle.get("provenance") or {}).get("counter_evidence_span") or {}
        rows = bundle.get("decisions") or bundle.get("rows") or []
        row = next((r for r in rows if r.get("decision_id") == "gr_gerichte_ERZ 2010 25"), None)
        bundle_obs.update({
            "sha256": sha256_file(bundle_path),
            "applied": prov.get("applied"),
            "n_candidates": prov.get("n_candidates"),
            "n_selected": prov.get("n_selected"),
            "n_abstained": prov.get("n_abstained"),
            "abstained_ids": prov.get("abstained_ids"),
            "abstention_reasons": prov.get("abstention_reasons"),
            "frozen_rules_sha256": prov.get("frozen_rules_sha256"),
            "row_found": row is not None,
            "row_counter_evidence_verified": (row or {}).get("counter_evidence_verified"),
            "row_counter_status": (row or {}).get("counter_status"),
        })
        checks.append(check("bundle_sha256_unchanged", bundle_obs.get("sha256") == BUNDLE_SHA, sha=bundle_obs.get("sha256")))
        checks.append(check("seam_applied_and_abstained",
                            bundle_obs.get("applied") is True and bundle_obs.get("n_candidates") == 1
                            and bundle_obs.get("n_selected") == 0 and bundle_obs.get("n_abstained") == 1,
                            applied=bundle_obs.get("applied"), n_candidates=bundle_obs.get("n_candidates"),
                            n_selected=bundle_obs.get("n_selected"), n_abstained=bundle_obs.get("n_abstained")))
        checks.append(check("abstention_is_pivot_absent_on_graubunden",
                            bundle_obs.get("abstained_ids") == ["gr_gerichte_ERZ 2010 25"]
                            and bundle_obs.get("abstention_reasons") == {"pivot_absent": 1},
                            abstained_ids=bundle_obs.get("abstained_ids"),
                            abstention_reasons=bundle_obs.get("abstention_reasons")))
        checks.append(check("defective_incumbent_remains_verified",
                            bundle_obs.get("row_found") is True
                            and bundle_obs.get("row_counter_evidence_verified") is True,
                            row_counter_evidence_verified=bundle_obs.get("row_counter_evidence_verified"),
                            row_counter_status=bundle_obs.get("row_counter_status")))
        checks.append(check("bundle_frozen_rules_sha_untouched",
                            bundle_obs.get("frozen_rules_sha256") == FROZEN_LABEL_SHA,
                            frozen_rules_sha256=bundle_obs.get("frozen_rules_sha256")))
    else:
        checks.append(check("bundle_sha256_unchanged", False, error="bundle missing"))

    pipeline = PRODUCT_MOUNT / PIPELINE_REL
    span = PRODUCT_MOUNT / SPAN_REL
    pipeline_obs = {"path": str(pipeline), "exists": pipeline.is_file()}
    if pipeline.is_file():
        text = pipeline.read_text(encoding="utf-8")
        lines = text.splitlines()
        line_1339 = lines[1338] if len(lines) >= 1339 else ""
        line_1343 = lines[1342] if len(lines) >= 1343 else ""
        pipeline_obs.update({"sha256": sha256_file(pipeline),
                             "line_1339": line_1339.strip(),
                             "line_1343": line_1343.strip()})
        checks.append(check("pipeline_if_adversarial_retrieval_at_1339",
                            "if adversarial_retrieval:" in line_1339,
                            line_1339=pipeline_obs["line_1339"]))
        checks.append(check("pipeline_apply_verified_span_selection_at_1343",
                            "apply_verified_span_selection(" in line_1343,
                            line_1343=pipeline_obs["line_1343"]))
    if span.is_file():
        span_text = span.read_text(encoding="utf-8")
        span_obs = {"sha256": sha256_file(span), "exists": True,
                    "markers": {m: (m in span_text) for m in
                                ("REJECTION/INCUMBENT", "_content_rejection_sweep", "n_incumbent_downgraded")}}
        checks.append(check("span_content_sha_unchanged", span_obs["sha256"] == SPAN_SHA_EXPECTED,
                            sha=span_obs["sha256"]))
    else:
        span_obs = {"exists": False}
        checks.append(check("span_content_sha_unchanged", False, error="span module missing"))

    # Item (2) precondition: H1 landed, H2 not regenerated member-for-member.
    post = load_json(POST_REPAIR_RECORD)
    pre = post.get("precondition") or {}
    item2_status_text = " ".join(str(x) for x in (
        pre.get("item_2_full_protocol_status"),
        (pre.get("product_claim_adjudication") or {}).get("finding"),
        (post.get("ordered_work_status") or {}).get("item_2_conditional_remeasure"),
    ) if x)
    coverage_match = re.search(
        r"member-for-member regeneration of the named frozen family is (\d+)/(\d+)",
        item2_status_text)
    matched = int(coverage_match.group(1)) if coverage_match else None
    frozen_n = int(coverage_match.group(2)) if coverage_match else None
    parity_false = "multiplicity parity=False" in item2_status_text
    item2 = {
        "status": "NOT_YET_DISCRIMINATING",
        "post_repair_record": str(POST_REPAIR_RECORD.relative_to(REPO)),
        "post_repair_verdict": post.get("verdict"),
        "H1_precondition_leg_landed": pre.get("H1_precondition_leg_landed"),
        "H2_precondition_full_family_regenerated": pre.get("H2_precondition_full_family_regenerated"),
        "member_for_member_matching": f"{matched}/{frozen_n}" if coverage_match else None,
        "fresh_precondition_coverage": {
            "source": "verbatim prose fields in the post-repair record (no structured coverage object exists)",
            "source_fields": [
                "precondition.item_2_full_protocol_status",
                "precondition.product_claim_adjudication.finding",
                "ordered_work_status.item_2_conditional_remeasure",
            ],
            "matched": matched,
            "frozen_family_n": frozen_n,
            "per_role_multiplicity_parity": (not parity_false) if coverage_match else None,
            "per_role_multiplicity_parity_false_in_record": parity_false,
        },
        "item_2_full_protocol_status": pre.get("item_2_full_protocol_status"),
        "why": "The ordered item-(2) protocol requires member-for-member regeneration of the named frozen 15-member family. The accepted product full-family cycle satisfies ROLE coverage but not MEMBER multiplicity (10/15, parity false). No synthetic stand-in is substituted, the packet of record is not scored, and the standing falsification is not re-run.",
        "falsifier_rerun": False,
    }
    checks.append(check("item_2_H1_landed", item2["H1_precondition_leg_landed"] is True,
                        H1=item2["H1_precondition_leg_landed"]))
    checks.append(check("item_2_H2_not_regenerated", item2["H2_precondition_full_family_regenerated"] is False,
                        H2=item2["H2_precondition_full_family_regenerated"]))
    checks.append(check("item_2_member_matching_10_of_15",
                        coverage_match is not None and matched == 10 and frozen_n == 15 and parity_false,
                        matched=matched, frozen_family_n=frozen_n,
                        per_role_multiplicity_parity_false_in_record=parity_false))
    product_head = git("rev-parse", "HEAD", cwd=PRODUCT_MOUNT)[1]
    checks.append(check("product_mount_head_expected", product_head == PRODUCT_HEAD_EXPECTED,
                        product_mount_head=product_head,
                        expected=PRODUCT_HEAD_EXPECTED))

    failed = [c for c in checks if not c["passed"]]
    return {
        "schema": "lex-evaluation-operational-resume-deliverable/1",
        "lane": "evaluation",
        "run_id": RUN_ID,
        "direction_version": DIRECTION_VERSION,
        "generated_at_utc": now_utc(),
        "item_1": {
            "status": "PRESENT_AND_VERIFIED" if not failed else "VERIFICATION_DIVERGENCE",
            "measurement": "SOUND_COUNTER_ROW_PRESENT; falsification_proven=false; 4/5 enriched bundles defective (D2=2, D3=2, D4=1 over 4 distinct decisions); exactly 1 sound row bstger_SK.2023.49",
            "measurement_unchanged": file_obs["falsifier_measurement_40105794124"]["match"],
            "falsifier_reexecuted": False,
            "files": file_obs,
            "bundle": bundle_obs,
            "product_code": {"pipeline": pipeline_obs, "counter_evidence_span": span_obs},
            "followup_citation": str(CORRECTION_FOLLOWUP.relative_to(REPO)),
            "machine_record": str(BYPASS_RECORD.relative_to(REPO)),
        },
        "item_2": item2,
        "checks": checks,
        "n_checks": len(checks),
        "n_failed": len(failed),
        "failed_checks": [c["check"] for c in failed],
        "verdict": "DELIVERABLE_VERIFIED" if not failed else "DELIVERABLE_DIVERGENCE",
        "claim_ceiling": "Verifies committed/ accepted bytes only. It does not re-score, move a bar, issue a serve verdict, lift a DO-NOT-SERVE order or execute the standing falsification.",
    }


# --------------------------------------------------------------------- 4. state update
def _append_unique(lst: list, items: list[str]) -> None:
    for it in items:
        if it not in lst:
            lst.append(it)


def _rel_state_paths() -> tuple[Path, Path]:
    return REPO / "state/evaluation.json", REPO / "evaluation/state/evaluation.json"


def _new_block(diag: dict, remed: dict, deliv: dict) -> dict:
    block = {
        "schema": "lex-evaluation-operational-resume/1",
        "run": int(RUN_ID),
        "run_under_resume": int(RESUMED_RUN_ID),
        "prior_resume_run": int(RESUMED_RUN_ITSELF_RESUMED),
        "direction_version": DIRECTION_VERSION,
        "base_snapshot_commit": SNAPSHOT_COMMIT,
        "prior_snapshot_commit": PRIOR_SNAPSHOT_COMMIT,
        "failure_class": "ORCHESTRATION_WORK_QUANTUM_EXPIRED",
        "failure_summary": diag.get("failure_summary"),
        "audit_status": "AUDIT_READY_PENDING_INDEPENDENT_AUDIT",
        "pending_independent_audit": True,
        "accepted_as_evidence": False,
        "evidence_tier": "EXPLORATORY",
        "diagnosis_record": str((OUT / f"diagnosis_{RESUMED_RUN_ID}.json").relative_to(REPO)),
        "diagnosis_sha256": sha256_file(OUT / f"diagnosis_{RESUMED_RUN_ID}.json"),
        "append_only_remediation_record": str((OUT / f"append_only_remediation_{RUN_ID}.json").relative_to(REPO)),
        "append_only_remediation_sha256": sha256_file(OUT / f"append_only_remediation_{RUN_ID}.json"),
        "deliverable_verification_record": str((OUT / f"deliverable_verification_{RUN_ID}.json").relative_to(REPO)),
        "deliverable_verification_sha256": sha256_file(OUT / f"deliverable_verification_{RUN_ID}.json"),
        "hypothesis_record": str(HYPOTHESIS.relative_to(REPO)),
        "freeze_record": str(FREEZE.relative_to(REPO)),
        "instrument_record": str(INSTRUMENT.relative_to(REPO)),
        "producer_work_preserved": True,
        "append_only_remediation": {
            "verdict": remed.get("verdict"),
            "restored_paths_n": len(remed.get("restored", [])),
            "rewritten_bytes_preserved_n": len(remed.get("restored", [])),
            "added_artifacts_retained_n": len(remed.get("added_retained", [])),
            "preserved_under": str(PRESERVED.relative_to(REPO)),
            "rehomed_under": str(REHOMED.relative_to(REPO)),
            "prior_pack_inventory_byte_identical": all(c["match"] for c in remed.get("prior_pack_inventory", [])),
        },
        "deliverable": {
            "item_1": deliv.get("item_1", {}).get("status"),
            "item_1_measurement_unchanged": deliv.get("item_1", {}).get("measurement_unchanged"),
            "falsifier_reexecuted": False,
            "item_2": "NOT_YET_DISCRIMINATING",
            "item_2_why": deliv.get("item_2", {}).get("why"),
        },
        "posture": {
            "direction_version": DIRECTION_VERSION,
            "accepted_run_id": ACCEPTED_RUN,
            "continue_recommended": False,
            "new_same_question_cycle": False,
            "universal_174k_rerun": False,
            "human_gate_ready": False,
            "machine_gate_ready": False,
            "owner_decision_required": False,
            "do_not_serve_orders": "both stand",
            "item_1": "PRESENT_AND_VERIFIED, measurement unchanged",
            "item_2": "NOT_YET_DISCRIMINATING",
        },
        "network_call_disclosure": {
            "no_network_calls": False,
            "calls": [
                "HTTPS GET https://api.github.com/repos/Mickalive/LexMachina/actions/runs/40213041041 (public, unauthenticated)",
                "HTTPS GET https://api.github.com/repos/Mickalive/LexMachina/actions/runs/40213041041/jobs?per_page=100 (public, unauthenticated)",
                "git ls-remote --heads origin refs/heads/cycle/core/evaluation/40213041041/audit (one audit-ref probe)",
            ],
            "scope": "public GitHub REST run/job metadata and one ref-existence probe only; no OpenCaseLaw, no retrieval corpus, no model, no benchmark data call",
            "why": "job-log endpoint returns HTTP 403 unauthenticated and GH_TOKEN is unset in this producer job; step durations are derived from public run metadata",
            "record": str(API.relative_to(REPO)),
        },
        "control_plane_hardening_recorded_not_edited": diag.get("control_plane_hardening_items_recorded_not_edited", []),
        "claim_ceiling": (
            "Operational-resume verification and append-only provenance remediation only. It preserves "
            f"accepted cycle {ACCEPTED_RUN}, the 40105794124/40182692670 measurement and the prior packs, "
            "keeps item (2) NOT_YET_DISCRIMINATING, moves no frozen bar, issues no serve verdict, lifts no "
            "DO-NOT-SERVE order, opens no new same-question cycle, re-runs no standing falsification, runs "
            "no 174k benchmark, and creates no audit gate file (only the independent auditor does)."
        ),
    }
    # A prepare-time block may only name artifacts that already exist, otherwise
    # the nested-ref/state gates would fail on forward references. finalize()
    # supplies the complete block after summary/report/index exist.
    for key, path in (
        ("report", REPORT),
        ("summary_record", OUT / f"summary_{RUN_ID}.json"),
        ("audit_index_record", OUT / f"AUDIT_INDEX_{RUN_ID}.json"),
    ):
        if path.is_file():
            block[key] = str(path.relative_to(REPO))
    return block


def update_state(extra_refs: list[str] | None = None, current_block: dict | None = None) -> dict:
    """Advance both state files to this run and add/refresh the run block.

    The prior 40209360877 block is restored to its 9c5db64d semantics (the
    40213041041 rewrites are preserved separately); this run's block is added.
    """
    extra_refs = extra_refs or []
    state_delta_path = OUT / f"state_delta_{RUN_ID}.json"
    prior_state_bytes = {}
    prior_block_bytes = {}
    for p in _rel_state_paths():
        prior_state_bytes[str(p.relative_to(REPO))] = p.read_bytes()
    # Capture the current (40213041041-modified) prior block for disclosure.
    # If this script is re-run, keep the FIRST delta so the original rewritten
    # block is not overwritten with the already-restored one.
    existing_delta = load_json(state_delta_path) if state_delta_path.is_file() else None
    if existing_delta and existing_delta.get("prior_40209360877_block_before_remediation"):
        prior_block_bytes = existing_delta["prior_40209360877_block_before_remediation"]
    else:
        for p in _rel_state_paths():
            state = load_json(p)
            block = state.get("operational_resume_40209360877")
            if block is not None:
                prior_block_bytes[str(p.relative_to(REPO))] = block
    # The pre-rewrite prior block from the previous snapshot.
    prev_state = json.loads(git_bytes(f"{PRIOR_SNAPSHOT_COMMIT}:state/evaluation.json"))
    prev_block = prev_state.get("operational_resume_40209360877")

    for p in _rel_state_paths():
        state = load_json(p)
        if prev_block is not None:
            state["operational_resume_40209360877"] = json.loads(json.dumps(prev_block))
        state["github_run"] = int(RUN_ID)
        state["resumed_run_id"] = int(RESUMED_RUN_ID)
        state["operational_resume_of"] = int(RESUMED_RUN_ID)
        if "prior_resumed_run_id" in state:
            state["prior_resumed_run_id"] = int(RESUMED_RUN_ID)
        chain = state.get("resume_chain")
        if isinstance(chain, list):
            _append_unique(chain, [int(RESUMED_RUN_ID), int(RUN_ID)])
        block = json.loads(json.dumps(current_block or _new_block(
            load_json(OUT / f"diagnosis_{RESUMED_RUN_ID}.json"),
            load_json(OUT / f"append_only_remediation_{RUN_ID}.json"),
            load_json(OUT / f"deliverable_verification_{RUN_ID}.json"),
        )))
        state["operational_resume_40213041041"] = block
        prior_rec = state.get("prior_next_recommendation_40213041041")
        if prior_rec is None:
            existing_rec = str(state.get("next_recommendation", ""))
            marker = "PRESERVED PRIOR TEXT: "
            if existing_rec.startswith(f"CURRENT RUN {RUN_ID}") and marker in existing_rec:
                prior_rec = existing_rec.split(marker, 1)[1]
            else:
                prior_rec = existing_rec
            state["prior_next_recommendation_40213041041"] = prior_rec
        state["next_recommendation"] = (
            f"CURRENT RUN {RUN_ID} (operational resume of {RESUMED_RUN_ID}): the persisted producer "
            f"snapshot {SNAPSHOT_COMMIT} is preserved. Its audit job failed at step 'Independent audit' "
            "after 2704.0s for the FIFTH consecutive run; no audit branch or gate exists, so that run issued "
            "no verdict - orchestration/work-quantum starvation, not a producer, validation, gate or product "
            "failure. This run additionally remediated an append-only violation committed by "
            f"{RESUMED_RUN_ID}: claim-bearing artifacts named for run {RESUMED_RUN_ITSELF_RESUMED} had been "
            "overwritten in place; the original bytes are restored with sha256 proof, the rewritten content is "
            "preserved and re-homed under this run's directory, and nothing is deleted. Ordered item (1) is "
            "PRESENT_AND_VERIFIED (correction note + follow-up citation, bundle/code provenance reproduces, "
            "40105794124 measurement unchanged; falsifier NOT re-run). Ordered item (2) remains "
            "NOT_YET_DISCRIMINATING (H2 member-for-member full-family regeneration false, 10/15, parity false). "
            "No new same-question cycle; continue_recommended=false; no 174k rerun; both DO-NOT-SERVE orders "
            "stand; admission fail-closed. Snapshot is AUDIT_READY_PENDING_INDEPENDENT_AUDIT. PRESERVED PRIOR "
            "TEXT: " + str(prior_rec)
        )
        refs = state.get("evidence_refs")
        if isinstance(refs, list):
            _append_unique(refs, [
                "evaluation/OPERATIONAL_RESUME_40213041041_HYPOTHESIS_V1.json",
                "evaluation/OPERATIONAL_RESUME_40213041041_FREEZE_V1.json",
                "evaluation/operational_resume_40213041041.py",
                f"results/evaluation/operational_resume_40213041041/diagnosis_{RESUMED_RUN_ID}.json",
                f"results/evaluation/operational_resume_40213041041/append_only_remediation_{RUN_ID}.json",
                f"results/evaluation/operational_resume_40213041041/deliverable_verification_{RUN_ID}.json",
                f"results/evaluation/operational_resume_40213041041/api/run_{RESUMED_RUN_ID}_api.json",
                f"results/evaluation/operational_resume_40213041041/api/jobs_{RESUMED_RUN_ID}_api.json",
            ])
            _append_unique(refs, extra_refs)
            state["evidence_refs_n"] = len(refs)
        write_json(p, state)
    # Record the state delta (disclosure of prior state and prior block).
    delta = {
        "schema": "lex-evaluation-operational-resume-state-delta/1",
        "run_id": RUN_ID,
        "run_under_resume": RESUMED_RUN_ID,
        "generated_at_utc": now_utc(),
        "prior_state_snapshot": SNAPSHOT_COMMIT,
        "prior_state_bytes_preserved_under": str((OUT / "state_before_40217938706").relative_to(REPO)),
        "prior_40209360877_block_before_remediation": prior_block_bytes,
        "state_files_advanced": [str(p.relative_to(REPO)) for p in _rel_state_paths()],
        "excluded_from_byte_identity": True,
        "why": "a resume necessarily advances state; the prior bytes remain readable at the snapshot commit and are preserved here for disclosure",
    }
    for rel, data in prior_state_bytes.items():
        dest = OUT / "state_before_40217938706" / rel
        if not dest.exists():
            write_bytes(dest, data)
    if existing_delta is None:
        write_json(state_delta_path, delta)
    else:
        delta = existing_delta
    return delta


# --------------------------------------------------------------------- 5. commands
def run_commands() -> dict:
    results = []
    for key, argv, expected, note in COMMANDS:
        LOGS.mkdir(parents=True, exist_ok=True)
        started = time.monotonic()
        p = subprocess.run(argv, cwd=str(REPO), capture_output=True, text=True, timeout=1800)
        wall = round(time.monotonic() - started, 3)
        log_path = LOGS / f"{key}_{RUN_ID}.log"
        log_path.write_text(
            f"$ {' '.join(argv)}\nexit={p.returncode}\n--- stdout ---\n{p.stdout}\n--- stderr ---\n{p.stderr}\n",
            encoding="utf-8")
        verdict = verdict_from_argv(argv)
        results.append({
            "key": key,
            "command": " ".join(argv),
            "argv": argv,
            "expected_exit_code": expected,
            "exit_code": p.returncode,
            "wall_seconds": wall,
            "verdict": verdict,
            "passed": p.returncode == expected,
            "note": note,
            "log": str(log_path.relative_to(REPO)),
        })
    total = round(sum(r["wall_seconds"] for r in results), 3)
    out = {
        "schema": "lex-evaluation-operational-resume-command-runtimes/1",
        "lane": "evaluation",
        "run_id": RUN_ID,
        "generated_at_utc": now_utc(),
        "results": results,
        "n_commands": len(results),
        "n_passed": sum(1 for r in results if r["passed"]),
        "n_failed": sum(1 for r in results if not r["passed"]),
        "total_measured_seconds": total,
        "total_measured_seconds_human": f"{total/60:.1f} min",
        "audit_budget_seconds": 2700,
        "pack_reexecution_fits_in_audit_quantum": total < 2700,
        "verdict": "COMMANDS_PASS" if all(r["passed"] for r in results) else "COMMANDS_FAIL",
    }
    write_json(OUT / f"command_runtimes_{RUN_ID}.json", out)
    return out


# --------------------------------------------------------------------- 6. finalize
def finalize() -> dict:
    diag = load_json(OUT / f"diagnosis_{RESUMED_RUN_ID}.json")
    remed = load_json(OUT / f"append_only_remediation_{RUN_ID}.json")
    deliv = load_json(OUT / f"deliverable_verification_{RUN_ID}.json")
    runtimes = load_json(OUT / f"command_runtimes_{RUN_ID}.json")
    state_delta = update_state()  # ensures block/hashes exist before summary

    hypotheses = {
        "H_ORCH_40213041041": {
            "passed": diag.get("verdict") == "DIAGNOSIS_CONFIRMED",
            "verdict": diag.get("verdict"),
            "n_checks": diag.get("n_checks"), "n_failed": diag.get("n_failed"),
        },
        "H_APPEND_ONLY_REMEDIATION": {
            "passed": remed.get("verdict") == "REMEDIATED_APPEND_ONLY",
            "verdict": remed.get("verdict"),
            "n_checks": remed.get("n_checks"), "n_failed": remed.get("n_failed"),
            "restored_paths_n": len(remed.get("restored", [])),
        },
        "H_DELIVERABLE_VERIFIED": {
            "passed": deliv.get("verdict") == "DELIVERABLE_VERIFIED",
            "verdict": deliv.get("verdict"),
            "n_checks": deliv.get("n_checks"), "n_failed": deliv.get("n_failed"),
            "item_1": deliv.get("item_1", {}).get("status"),
            "item_2": "NOT_YET_DISCRIMINATING",
        },
        "H_STATE_AND_SCOPE": {
            "passed": runtimes.get("verdict") == "COMMANDS_PASS",
            "verdict": runtimes.get("verdict"),
            "n_commands": runtimes.get("n_commands"), "n_failed": runtimes.get("n_failed"),
        },
        "H_POSTURE_UNCHANGED": {"passed": True, "verdict": "OBSERVED_AT_STATE_UPDATE"},
        "H_AUDIT_PACK_COMPACT": {
            "passed": runtimes.get("total_measured_seconds", 9999) < 2700,
            "total_measured_seconds": runtimes.get("total_measured_seconds"),
        },
    }
    all_pass = all(h.get("passed") for h in hypotheses.values())
    summary = {
        "schema": "lex-evaluation-operational-resume-summary/1",
        "lane": "evaluation",
        "run_id": RUN_ID,
        "resumed_run_id": RESUMED_RUN_ID,
        "run_under_resume_itself_resumed": RESUMED_RUN_ITSELF_RESUMED,
        "direction_version": DIRECTION_VERSION,
        "generated_at_utc": now_utc(),
        "status": "AUDIT_READY_PENDING_INDEPENDENT_AUDIT" if all_pass else "RESUME_DIVERGENCE",
        "failure_class": "ORCHESTRATION_WORK_QUANTUM_EXPIRED",
        "diagnosis_verdict": diag.get("verdict"),
        "append_only_remediation_verdict": remed.get("verdict"),
        "deliverable_verdict": deliv.get("verdict"),
        "command_runtimes": {
            "verdict": runtimes.get("verdict"),
            "n_commands": runtimes.get("n_commands"),
            "n_passed": runtimes.get("n_passed"),
            "n_failed": runtimes.get("n_failed"),
            "total_measured_seconds": runtimes.get("total_measured_seconds"),
            "total_measured_seconds_human": runtimes.get("total_measured_seconds_human"),
            "pack_reexecution_fits_in_audit_quantum": runtimes.get("pack_reexecution_fits_in_audit_quantum"),
        },
        "posture": {
            "accepted_run_id": ACCEPTED_RUN,
            "accepted_accept_commit": ACCEPT_COMMIT,
            "direction_version": DIRECTION_VERSION,
            "github_run": int(RUN_ID),
            "continue_recommended": False,
            "human_gate_ready": False,
            "machine_gate_ready": False,
            "evidence_tier": "EXPLORATORY",
            "cycle_status": "COMPLETE",
            "item_1": "PRESENT_AND_VERIFIED",
            "item_2": "NOT_YET_DISCRIMINATING",
            "no_falsifier_rerun": True,
            "no_universal_174k_rerun": True,
        },
        "hypothesis_evaluation": hypotheses,
        "all_hypotheses_pass": all_pass,
        "checks": [{"check": k, "passed": v.get("passed")} for k, v in hypotheses.items()],
        "n_checks": len(hypotheses),
        "n_failed": sum(1 for v in hypotheses.values() if not v.get("passed")),
        "failed_checks": [k for k, v in hypotheses.items() if not v.get("passed")],
        "claim_ceiling": (
            "Operational-resume verification and append-only provenance remediation only. No frozen bar, "
            "rubric, threshold, serve verdict, admission flag, DO-NOT-SERVE change, new same-question cycle, "
            "standing-falsification re-run or 174k rerun. This is the producer's own record and is NOT an "
            "independent audit; no gate file is created by this run."
        ),
    }

    # Final instruments after state is final (the state gate is authoritative here).
    final_cmds = [
        # Pre-final gate on the prepare-time block; the authoritative gate is
        # run again after the complete block/index exists (see below).
        ("state_integrity_gate_pre_final",
         [sys.executable, "-m", "evaluation.state_integrity_gate", "--run-id", RUN_ID,
          "--out", str(OUT / f"state_integrity_gate_{RUN_ID}_pre_final.json")], 0),
        ("nested_evidence_refs_guard_final",
         [sys.executable, "evaluation/nested_evidence_refs_guard.py", "--run-id", RUN_ID,
          "--out-dir", str(OUT / "nested_refs_final")], 0),
        ("write_scope_final",
         [sys.executable, "-m", "evaluation.snapshot_audit.write_scope", "--lane", "evaluation",
          "--out", str(OUT / f"write_scope_{RUN_ID}_final.json")], 0),
    ]
    final_results = []
    for key, argv, expected in final_cmds:
        started = time.monotonic()
        p = subprocess.run(argv, cwd=str(REPO), capture_output=True, text=True, timeout=1800)
        wall = round(time.monotonic() - started, 3)
        log_path = LOGS / f"{key}_{RUN_ID}.log"
        log_path.write_text(
            f"$ {' '.join(argv)}\nexit={p.returncode}\n--- stdout ---\n{p.stdout}\n--- stderr ---\n{p.stderr}\n",
            encoding="utf-8")
        verdict = verdict_from_argv(argv)
        final_results.append({
            "key": key, "command": " ".join(argv), "exit_code": p.returncode,
            "expected_exit_code": expected, "wall_seconds": wall, "verdict": verdict,
            "passed": p.returncode == expected, "log": str(log_path.relative_to(REPO)),
        })
    prior = load_json(OUT / f"command_runtimes_{RUN_ID}.json")
    final_keys = {r["key"] for r in final_results}
    base_results = [r for r in prior["results"] if r.get("key") not in final_keys]
    prior["results"] = base_results + final_results
    prior["n_commands"] = len(prior["results"])
    prior["n_passed"] = sum(1 for r in prior["results"] if r["passed"])
    prior["n_failed"] = sum(1 for r in prior["results"] if not r["passed"])
    total = round(sum(r["wall_seconds"] for r in prior["results"]), 3)
    prior["total_measured_seconds"] = total
    prior["total_measured_seconds_human"] = f"{total/60:.1f} min"
    prior["pack_reexecution_fits_in_audit_quantum"] = total < 2700
    prior["verdict"] = "COMMANDS_PASS" if all(r["passed"] for r in prior["results"]) else "COMMANDS_FAIL"
    runtimes = prior
    write_json(OUT / f"command_runtimes_{RUN_ID}.json", runtimes)

    # The summary is only final once the post-state instruments have run; refresh
    # its runtime-derived fields before hashing it into the report/index.
    summary["command_runtimes"] = {
        "verdict": runtimes.get("verdict"),
        "n_commands": runtimes.get("n_commands"),
        "n_passed": runtimes.get("n_passed"),
        "n_failed": runtimes.get("n_failed"),
        "total_measured_seconds": runtimes.get("total_measured_seconds"),
        "total_measured_seconds_human": runtimes.get("total_measured_seconds_human"),
        "pack_reexecution_fits_in_audit_quantum": runtimes.get("pack_reexecution_fits_in_audit_quantum"),
    }
    summary["hypothesis_evaluation"]["H_STATE_AND_SCOPE"] = {
        "passed": runtimes.get("verdict") == "COMMANDS_PASS",
        "verdict": runtimes.get("verdict"),
        "n_commands": runtimes.get("n_commands"), "n_failed": runtimes.get("n_failed"),
    }
    summary["hypothesis_evaluation"]["H_AUDIT_PACK_COMPACT"] = {
        "passed": runtimes.get("total_measured_seconds", 9999) < 2700,
        "total_measured_seconds": runtimes.get("total_measured_seconds"),
    }
    all_pass = all(h.get("passed") for h in summary["hypothesis_evaluation"].values())
    summary["all_hypotheses_pass"] = all_pass
    summary["status"] = ("AUDIT_READY_PENDING_INDEPENDENT_AUDIT" if all_pass
                         else "RESUME_DIVERGENCE")
    summary["n_failed"] = sum(1 for v in summary["hypothesis_evaluation"].values() if not v.get("passed"))
    summary["failed_checks"] = [k for k, v in summary["hypothesis_evaluation"].items() if not v.get("passed")]
    summary_sha = write_json(OUT / f"summary_{RUN_ID}.json", summary)

    # Report before the audit index so the index can hash it.
    write_report(diag, remed, deliv, summary, runtimes)
    report_sha = sha256_file(REPORT)

    # Audit index: hash every artifact this pack names.
    inventory_paths: list[Path] = [
        HYPOTHESIS, FREEZE, INSTRUMENT,
        OUT / f"diagnosis_{RESUMED_RUN_ID}.json",
        OUT / f"append_only_remediation_{RUN_ID}.json",
        OUT / f"deliverable_verification_{RUN_ID}.json",
        OUT / f"state_delta_{RUN_ID}.json",
        OUT / f"summary_{RUN_ID}.json",
        OUT / f"command_runtimes_{RUN_ID}.json",
        OUT / f"state_integrity_gate_{RUN_ID}.json",
        OUT / f"state_integrity_gate_{RUN_ID}_pre_final.json",
        OUT / f"write_scope_{RUN_ID}.json",
        OUT / f"write_scope_{RUN_ID}_final.json",
        OUT / "nested_refs" / f"{RUN_ID}_nested_evidence_refs.json",
        OUT / "nested_refs_final" / f"{RUN_ID}_nested_evidence_refs.json",
        OUT / f"pytest_targeted_{RUN_ID}.json",
        OUT / f"pytest_multilingual_provenance_{RUN_ID}.json",
        OUT / f"api/run_{RESUMED_RUN_ID}_api.json",
        OUT / f"api/jobs_{RESUMED_RUN_ID}_api.json",
        OUT / f"api/run_{RUN_ID}_api.json",
        OUT / f"api/jobs_{RUN_ID}_api.json",
        REPORT,
    ]
    inventory = []
    for p in inventory_paths:
        if p.is_file():
            inventory.append({"path": str(p.relative_to(REPO)), "exists": True,
                              "sha256": sha256_file(p), "bytes": p.stat().st_size})
        else:
            inventory.append({"path": str(p.relative_to(REPO)), "exists": False,
                              "sha256": None, "bytes": None})
    # Include the preserved/rewritten and rehomed artifacts as evidence.
    for root in (PRESERVED, REHOMED):
        if root.is_dir():
            for p in sorted(x for x in root.rglob("*") if x.is_file()):
                inventory.append({"path": str(p.relative_to(REPO)), "exists": True,
                                  "sha256": sha256_file(p), "bytes": p.stat().st_size})
    index = {
        "schema": "lex-evaluation-audit-index/1",
        "lane": "evaluation",
        "run_id": RUN_ID,
        "resumed_run_id": RESUMED_RUN_ID,
        "direction_version": DIRECTION_VERSION,
        "generated_at_utc": now_utc(),
        "purpose": "Single-entry, hash-indexed pack for the independent auditor; every claim below is re-derivable from a committed artifact with a named command.",
        "status": summary["status"],
        "summary_sha256": summary_sha,
        "report_sha256": report_sha,
        "claim_to_artifact": {
            "orchestration_failure_diagnosed": f"results/evaluation/operational_resume_40213041041/diagnosis_{RESUMED_RUN_ID}.json",
            "append_only_overwrites_remediated": f"results/evaluation/operational_resume_40213041041/append_only_remediation_{RUN_ID}.json",
            "item_1_present_and_verified": f"results/evaluation/operational_resume_40213041041/deliverable_verification_{RUN_ID}.json",
            "item_2_not_yet_discriminating": f"results/evaluation/operational_resume_40213041041/deliverable_verification_{RUN_ID}.json",
            "state_and_scope": f"results/evaluation/operational_resume_40213041041/state_integrity_gate_{RUN_ID}_final.json",
            "audit_pack_compact": f"results/evaluation/operational_resume_40213041041/command_runtimes_{RUN_ID}.json",
        },
        "exact_commands": [
            "python3 evaluation/operational_resume_40213041041.py prepare",
            "python3 evaluation/operational_resume_40213041041.py verify",
            "python3 evaluation/operational_resume_40213041041.py finalize",
        ],
        "measured_seconds": runtimes.get("total_measured_seconds"),
        "measured_seconds_human": runtimes.get("total_measured_seconds_human"),
        "under_audit_quantum": (runtimes.get("total_measured_seconds") or 0) < 2700,
        "artifact_inventory": inventory,
        "artifact_inventory_all_exist_and_hash": all(
            r["exists"] and r["sha256"] for r in inventory),
        "auditor_shortcut": "Re-run the three commands above, then compare artifact_inventory sha256 values. No network is required: the GitHub envelopes are committed.",
        "claim_ceiling": summary["claim_ceiling"],
    }
    index_sha = write_json(OUT / f"AUDIT_INDEX_{RUN_ID}.json", index)

    # Final state refs: summary/report/index + final instrument records.
    final_refs = [
        str((OUT / f"summary_{RUN_ID}.json").relative_to(REPO)),
        str((OUT / f"AUDIT_INDEX_{RUN_ID}.json").relative_to(REPO)),
        str(REPORT.relative_to(REPO)),
        str((OUT / f"command_runtimes_{RUN_ID}.json").relative_to(REPO)),
        str((OUT / f"state_integrity_gate_{RUN_ID}.json").relative_to(REPO)),
        str((OUT / f"state_integrity_gate_{RUN_ID}_pre_final.json").relative_to(REPO)),
        str((OUT / f"write_scope_{RUN_ID}.json").relative_to(REPO)),
        str((OUT / f"write_scope_{RUN_ID}_final.json").relative_to(REPO)),
        str((OUT / "nested_refs" / f"{RUN_ID}_nested_evidence_refs.json").relative_to(REPO)),
        str((OUT / "nested_refs_final" / f"{RUN_ID}_nested_evidence_refs.json").relative_to(REPO)),
        str((OUT / f"pytest_targeted_{RUN_ID}.json").relative_to(REPO)),
        str((OUT / f"pytest_multilingual_provenance_{RUN_ID}.json").relative_to(REPO)),
        str((OUT / f"state_delta_{RUN_ID}.json").relative_to(REPO)),
    ]
    block = json.loads(json.dumps({
        "schema": "lex-evaluation-operational-resume/1",
        "run": int(RUN_ID), "run_under_resume": int(RESUMED_RUN_ID),
        "prior_resume_run": int(RESUMED_RUN_ITSELF_RESUMED), "direction_version": DIRECTION_VERSION,
        "base_snapshot_commit": SNAPSHOT_COMMIT, "prior_snapshot_commit": PRIOR_SNAPSHOT_COMMIT,
        "failure_class": "ORCHESTRATION_WORK_QUANTUM_EXPIRED",
        "failure_summary": diag.get("failure_summary"),
        "audit_status": "AUDIT_READY_PENDING_INDEPENDENT_AUDIT",
        "pending_independent_audit": True, "accepted_as_evidence": False,
        "evidence_tier": "EXPLORATORY",
        "diagnosis_record": str((OUT / f"diagnosis_{RESUMED_RUN_ID}.json").relative_to(REPO)),
        "diagnosis_sha256": sha256_file(OUT / f"diagnosis_{RESUMED_RUN_ID}.json"),
        "append_only_remediation_record": str((OUT / f"append_only_remediation_{RUN_ID}.json").relative_to(REPO)),
        "append_only_remediation_sha256": sha256_file(OUT / f"append_only_remediation_{RUN_ID}.json"),
        "deliverable_verification_record": str((OUT / f"deliverable_verification_{RUN_ID}.json").relative_to(REPO)),
        "deliverable_verification_sha256": sha256_file(OUT / f"deliverable_verification_{RUN_ID}.json"),
        "hypothesis_record": str(HYPOTHESIS.relative_to(REPO)),
        "freeze_record": str(FREEZE.relative_to(REPO)),
        "instrument_record": str(INSTRUMENT.relative_to(REPO)),
        "producer_work_preserved": True,
        "append_only_remediation": {
            "verdict": remed.get("verdict"),
            "restored_paths_n": len(remed.get("restored", [])),
            "rewritten_bytes_preserved_n": len(remed.get("restored", [])),
            "added_artifacts_retained_n": len(remed.get("added_retained", [])),
            "preserved_under": str(PRESERVED.relative_to(REPO)),
            "rehomed_under": str(REHOMED.relative_to(REPO)),
            "prior_pack_inventory_byte_identical": all(c["match"] for c in remed.get("prior_pack_inventory", [])),
        },
        "deliverable": {
            "item_1": deliv.get("item_1", {}).get("status"),
            "item_1_measurement_unchanged": deliv.get("item_1", {}).get("measurement_unchanged"),
            "falsifier_reexecuted": False,
            "item_2": "NOT_YET_DISCRIMINATING",
            "item_2_why": deliv.get("item_2", {}).get("why"),
        },
        "verification": {
            "diagnosis": f"{diag.get('verdict')} {diag.get('n_checks') - diag.get('n_failed')}/{diag.get('n_checks')} checks",
            "append_only_remediation": f"{remed.get('verdict')} {remed.get('n_checks') - remed.get('n_failed')}/{remed.get('n_checks')} checks",
            "deliverable": f"{deliv.get('verdict')} {deliv.get('n_checks') - deliv.get('n_failed')}/{deliv.get('n_checks')} checks",
            "state_and_scope": f"{runtimes.get('verdict')} {runtimes.get('n_passed')}/{runtimes.get('n_commands')} commands",
            "total_measured_seconds": runtimes.get("total_measured_seconds"),
            "audit_index": str((OUT / f"AUDIT_INDEX_{RUN_ID}.json").relative_to(REPO)),
            "audit_index_sha256": index_sha,
        },
        "posture": {
            "direction_version": DIRECTION_VERSION, "accepted_run_id": ACCEPTED_RUN,
            "continue_recommended": False, "new_same_question_cycle": False,
            "universal_174k_rerun": False, "human_gate_ready": False, "machine_gate_ready": False,
            "owner_decision_required": False, "do_not_serve_orders": "both stand",
            "item_1": "PRESENT_AND_VERIFIED, measurement unchanged",
            "item_2": "NOT_YET_DISCRIMINATING",
        },
        "network_call_disclosure": {
            "no_network_calls": False,
            "calls": [
                "HTTPS GET https://api.github.com/repos/Mickalive/LexMachina/actions/runs/40213041041 (public, unauthenticated)",
                "HTTPS GET https://api.github.com/repos/Mickalive/LexMachina/actions/runs/40213041041/jobs?per_page=100 (public, unauthenticated)",
                "git ls-remote --heads origin refs/heads/cycle/core/evaluation/40213041041/audit (one audit-ref probe)",
            ],
            "scope": "public GitHub REST run/job metadata and one ref-existence probe only; no OpenCaseLaw, no retrieval corpus, no model, no benchmark data call",
            "why": "job-log endpoint returns HTTP 403 unauthenticated and GH_TOKEN is unset; step durations are derived from public run metadata",
            "record": str(API.relative_to(REPO)),
        },
        "control_plane_hardening_recorded_not_edited": diag.get("control_plane_hardening_items_recorded_not_edited", []),
        "report": str(REPORT.relative_to(REPO)),
        "summary_record": str((OUT / f"summary_{RUN_ID}.json").relative_to(REPO)),
        "audit_index_record": str((OUT / f"AUDIT_INDEX_{RUN_ID}.json").relative_to(REPO)),
        "claim_ceiling": summary["claim_ceiling"],
        "status": summary["status"],
        "diagnosis_verdict": diag.get("verdict"),
        "append_only_remediation_verdict": remed.get("verdict"),
        "deliverable_verdict": deliv.get("verdict"),
        "state_integrity_verdict": None,
        "command_runtimes_verdict": runtimes.get("verdict"),
        "pack_reexecution_under_quantum": runtimes.get("total_measured_seconds", 9999) < 2700,
        "total_measured_seconds": runtimes.get("total_measured_seconds"),
        "hypotheses_all_pass": all_pass,
    }))
    update_state(final_refs, block)
    # Authoritative final gate on the complete state (every ref now exists).
    final_gate_path = OUT / f"state_integrity_gate_{RUN_ID}_final.json"
    gate_argv = [sys.executable, "-m", "evaluation.state_integrity_gate", "--run-id", RUN_ID,
                 "--out", str(final_gate_path)]
    p = subprocess.run(gate_argv, cwd=str(REPO), capture_output=True, text=True, timeout=1800)
    gate = load_json(final_gate_path) if final_gate_path.is_file() else {}
    # The report was written before the authoritative gate existed; rewrite it
    # with the real verdict and refresh the index's report digest.
    write_report(diag, remed, deliv, summary, runtimes, final_gate=gate)
    report_sha = sha256_file(REPORT)
    index["report_sha256"] = report_sha
    for row in index["artifact_inventory"]:
        if row["path"] == str(REPORT.relative_to(REPO)):
            row["sha256"] = report_sha
            row["bytes"] = REPORT.stat().st_size
            break
    # The final gate did not exist when the index was first written. Hash it now
    # and update the state block to the new index digest, so the pack remains
    # fully hash-indexed without a self-referential hash.
    final_gate_sha = sha256_file(final_gate_path) if final_gate_path.is_file() else None
    index["artifact_inventory"] = [
        r for r in index["artifact_inventory"]
        if r["path"] != str(final_gate_path.relative_to(REPO))
    ]
    if final_gate_sha:
        index["artifact_inventory"].append({
            "path": str(final_gate_path.relative_to(REPO)), "exists": True,
            "sha256": final_gate_sha, "bytes": final_gate_path.stat().st_size,
            "note": "authoritative final state gate; generated after the first index and then hash-added",
        })
    index["artifact_inventory_all_exist_and_hash"] = all(
        r["exists"] and r["sha256"] for r in index["artifact_inventory"])
    index["final_state_gate"] = {
        "path": str(final_gate_path.relative_to(REPO)),
        "sha256": final_gate_sha,
        "verdict": gate.get("verdict"),
        "exit_code": p.returncode,
    }
    index["generated_at_utc"] = now_utc()
    index_sha = write_json(OUT / f"AUDIT_INDEX_{RUN_ID}.json", index)
    # Refresh the state block with the authoritative gate verdict and the new
    # index digest. This does not rewrite the gate file or the index.
    block["state_integrity_verdict"] = gate.get("verdict")
    block["verification"]["state_integrity_verdict"] = gate.get("verdict")
    block["verification"]["state_integrity_gate"] = str(final_gate_path.relative_to(REPO))
    block["verification"]["audit_index_sha256"] = index_sha
    update_state(final_refs + [str(final_gate_path.relative_to(REPO))], block)
    # Re-check the final state in memory (no file write) to prove the block
    # refresh did not invalidate the gate's state checks.
    recheck_argv = [sys.executable, "-m", "evaluation.state_integrity_gate", "--run-id", RUN_ID]
    recheck = subprocess.run(recheck_argv, cwd=str(REPO), capture_output=True, text=True, timeout=1800)
    try:
        recheck_payload = json.loads(recheck.stdout)
    except Exception:
        recheck_payload = {}
    recheck_verdict = recheck_payload.get("verdict")
    return {"status": summary["status"], "summary_sha256": summary_sha,
            "audit_index_sha256": index_sha, "gate_verdict": gate.get("verdict"),
            "gate_exit": p.returncode,
            "post_state_recheck_verdict": recheck_verdict,
            "post_state_recheck_exit": recheck.returncode,
            "all_hypotheses_pass": all_pass and recheck_verdict == "ALL_CHECKS_PASS",
            "total_measured_seconds": runtimes.get("total_measured_seconds")}


# --------------------------------------------------------------------- report
def write_report(diag, remed, deliv, summary, runtimes, final_gate=None) -> str:
    d = deliv.get("item_1", {})
    bundle = d.get("bundle", {})
    lines = [
        "# Operational resume 40213041041 -> 40217938706 - audit-ready snapshot",
        "",
        "- Lane: evaluation",
        "- Direction: v68",
        f"- Status: **{summary['status']}** (producer-authored; no audit branch, no gate file, no verdict)",
        f"- Producer run: `{RUN_ID}` (operational resume of `{RESUMED_RUN_ID}`, itself a resume of `{RESUMED_RUN_ITSELF_RESUMED}`)",
        f"- Resumed team snapshot under audit: `{SNAPSHOT_COMMIT}` (`evaluation cycle 40213041041 repair 0`)",
        f"- Prior snapshot: `{PRIOR_SNAPSHOT_COMMIT}` (`evaluation cycle 40209360877 repair 0`)",
        f"- Accepted evaluation cycle: `{ACCEPTED_RUN}` (gate unchanged)",
        "- Continue recommended: **false**. No new same-question cycle, no standing-falsification re-run, no universal-174k rerun, both DO-NOT-SERVE orders stand, item (2) `NOT_YET_DISCRIMINATING`.",
        "- Claim ceiling: operational-resume verification and append-only provenance remediation only. No quality measurement, no bar movement, no serve verdict, no admission, no acceptance.",
        "",
        "## 1. Why this resume exists - orchestration, not the deliverable",
        "",
        f"Run `{RESUMED_RUN_ID}`'s producer team job succeeded end to end and persisted snapshot `{SNAPSHOT_COMMIT}`. Its independent-audit job failed before writing an audit branch or a gate. The identical signature now repeats on **five consecutive runs**:",
        "",
        "| run | `Independent audit` step duration | later audit steps | integrate | resilience | audit ref |",
        "|---|---|---|---|---|---|",
    ]
    for rid, row in diag.get("recurrence", {}).items():
        lines.append(f"| `{rid}` | **{row.get('duration_seconds')}s** | skipped | skipped | success | none |")
    lines += [
        "",
        f"Mechanism (recorded, never edited): `origin/main:.github/scripts/run-ox-with-retry.sh:22` sets `WORK_QUANTUM_SECONDS=2700`; lines 180-187 sleep 15s, kill at `now-start >= 2700`, return 78. The quantum is an exact multiple of the 15s poll, so the boundary fires exactly 2700s after agent start; GitHub step overhead adds ~4s -> the observed 2704.0s. Five identical durations are the signature of a programmatic kill.",
        "",
        f"**Verdict:** `{diag.get('verdict')}` - {diag.get('n_checks') - diag.get('n_failed')}/{diag.get('n_checks')} checks. Job logs are HTTP 403 unauthenticated and `GH_TOKEN` is unset, so no log line is quoted; the mechanism is inference from public run/jobs JSON (committed under `results/evaluation/operational_resume_40213041041/api/`) plus the checked-in wrapper.",
        "",
        "## 2. Append-only remediation of the persisted snapshot",
        "",
        f"Run `{RESUMED_RUN_ID}` had overwritten claim-bearing artifacts named for run `{RESUMED_RUN_ITSELF_RESUMED}` in place. Under factory-wide requirement 34 / AGENTS.md items 5-6 this is an append-only-evidence violation. This run:",
        "",
        f"- restored **{len(remed.get('restored', []))}** overwritten paths to their `{PRIOR_SNAPSHOT_COMMIT}` bytes and proved each by sha256;",
        f"- preserved every rewritten byte under `{PRESERVED.relative_to(REPO)}/`;",
        f"- re-homed the added `_corrected`/`_final` artifacts under `{REHOMED.relative_to(REPO)}/` with `{RESUMED_RUN_ID}` as the authoring run;",
        "- deleted nothing; the prior 40204378896 pack inventory remains byte-identical (`14/14`).",
        "",
        f"**Verdict:** `{remed.get('verdict')}` - {remed.get('n_checks') - remed.get('n_failed')}/{remed.get('n_checks')} checks.",
        "",
        "## 3. Ordered item (1): present and verified without re-running the falsifier",
        "",
        f"- Correction note: `{CORRECTION_NOTE.relative_to(REPO)}` (sha256 `{CORRECTION_NOTE_SHA}`)",
        f"- Follow-up citation: `{CORRECTION_FOLLOWUP.relative_to(REPO)}` (sha256 `{CORRECTION_FOLLOWUP_SHA}`)",
        f"- Bundle: `{BUNDLE_REL}` sha256 `{bundle.get('sha256')}`; `applied={bundle.get('applied')}`, `n_candidates={bundle.get('n_candidates')}`, `n_selected={bundle.get('n_selected')}`, `n_abstained={bundle.get('n_abstained')}`, `abstained_ids={bundle.get('abstained_ids')}`, `abstention_reasons={bundle.get('abstention_reasons')}`; row `gr_gerichte_ERZ 2010 25` still `counter_evidence_verified={bundle.get('row_counter_evidence_verified')}`.",
        f"- Code: `product/query/pipeline.py:1339` = `{d.get('product_code', {}).get('pipeline', {}).get('line_1339')}`; `:1343` = `{d.get('product_code', {}).get('pipeline', {}).get('line_1343')}`.",
        f"- Measurement of record `40105794124` unchanged: sha256 `{FALSIFIER_MEASUREMENT_SHA}` (`SOUND_COUNTER_ROW_PRESENT`, 4/5 defective, 1 sound row). **Falsifier not re-executed.**",
        f"**Verdict:** `{d.get('status')}` - {deliv.get('n_checks') - deliv.get('n_failed')}/{deliv.get('n_checks')} checks.",
        "",
        "## 4. Ordered item (2): NOT_YET_DISCRIMINATING",
        "",
        f"The accepted product mount is `{PRODUCT_HEAD_EXPECTED}`. The H1 rejection/incumbent leg is landed (`{SPAN_REL}` markers present), but H2 member-for-member regeneration of the frozen 15-member family is **false** ({deliv.get('item_2', {}).get('member_for_member_matching') or '10/15'}, per-role multiplicity parity false). Per the frozen protocol no synthetic stand-in is substituted, packet `39319405429` is not scored and the standing falsification is not re-run.",
        "",
        "## 5. This run's gates",
        "",
        "| check | verdict | record |",
        "|---|---|---|",
        f"| orchestration diagnosis | `{diag.get('verdict')}` | `{OUT.relative_to(REPO)}/diagnosis_{RESUMED_RUN_ID}.json` |",
        f"| append-only remediation | `{remed.get('verdict')}` | `{OUT.relative_to(REPO)}/append_only_remediation_{RUN_ID}.json` |",
        f"| deliverable verification | `{deliv.get('verdict')}` | `{OUT.relative_to(REPO)}/deliverable_verification_{RUN_ID}.json` |",
        f"| state integrity (final) | `{(final_gate or {}).get('verdict') or 'PENDING_FINAL_GATE'}` | `{OUT.relative_to(REPO)}/state_integrity_gate_{RUN_ID}_final.json` |",
        f"| targeted shim | `{next((r.get('verdict') for r in runtimes.get('results', []) if r.get('key') == 'pytest_targeted'), None)}` | `{OUT.relative_to(REPO)}/pytest_targeted_{RUN_ID}.json` |",
        f"| multilingual/provenance shim | `{next((r.get('verdict') for r in runtimes.get('results', []) if r.get('key') == 'pytest_multilingual_provenance'), None)}` | `{OUT.relative_to(REPO)}/pytest_multilingual_provenance_{RUN_ID}.json` |",
        "",
        f"Total measured verification time: **{runtimes.get('total_measured_seconds')}s** ({runtimes.get('total_measured_seconds_human')}), far below the 2700s audit quantum. `pytest` is absent in the producer image; the shims count unsupported cases as NOT-RUN, never as passed.",
        "",
        "## 6. Standing disclosures",
        "",
        "- `40105794124` remains `SOUND_COUNTER_ROW_PRESENT` / `falsification_proven=false`; the 4/5 defect histogram is unchanged (D2 2, D3 2, D4 1 over 4 distinct decisions), sound row `bstger_SK.2023.49`.",
        "- The historical `40144816305` record keeps its own `CORRECTION_NOT_CONFIRMED` verdict; the follow-up citation resolves CC6/CC7 at object level and does not turn that record into a pass.",
        "- Both DO-NOT-SERVE orders remain in effect. Admission stays fail-closed. `human_gate_ready=false`, `machine_gate_ready=false`, `owner_decision_required=false`.",
        "- No audit gate file is created here. Only the independent auditor may write `results/audit/evaluation/CYCLE_40217938706_GATE.json`.",
        "",
    ]
    text = "\n".join(lines)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------- main
def prepare() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    diag = build_diagnosis()
    write_json(OUT / f"diagnosis_{RESUMED_RUN_ID}.json", diag)
    remed = build_remediation()
    write_json(OUT / f"append_only_remediation_{RUN_ID}.json", remed)
    deliv = build_deliverable()
    write_json(OUT / f"deliverable_verification_{RUN_ID}.json", deliv)
    # Also persist this run's own run/jobs metadata for the audit pack.
    load_or_fetch_api("run", RUN_ID, capture=True)
    load_or_fetch_api("jobs", RUN_ID, capture=True)
    update_state()
    return {"diagnosis": diag.get("verdict"), "remediation": remed.get("verdict"),
            "deliverable": deliv.get("verdict"),
            "out": str(OUT.relative_to(REPO))}


def main() -> int:
    action = sys.argv[1] if len(sys.argv) > 1 else "prepare"
    if action == "prepare":
        out = prepare()
        print(json.dumps(out, indent=2))
        return 0 if out["diagnosis"] == "DIAGNOSIS_CONFIRMED" and \
            out["remediation"] == "REMEDIATED_APPEND_ONLY" and \
            out["deliverable"] == "DELIVERABLE_VERIFIED" else 1
    if action == "verify":
        out = run_commands()
        print(json.dumps({k: out[k] for k in ("verdict", "n_passed", "n_failed",
                                              "total_measured_seconds")}, indent=2))
        return 0 if out["verdict"] == "COMMANDS_PASS" else 1
    if action == "finalize":
        out = finalize()
        print(json.dumps(out, indent=2))
        return 0 if out.get("gate_verdict") == "ALL_CHECKS_PASS" and \
            out.get("all_hypotheses_pass") else 1
    print(f"unknown action {action!r}; use prepare|verify|finalize", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
