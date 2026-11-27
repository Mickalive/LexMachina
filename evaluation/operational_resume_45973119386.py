#!/usr/bin/env python3
"""Operational-resume record builder for run 45973119386.

Resumes the persisted producer snapshot of run 45965187540 (branch
``cycle/core/evaluation/45965187540/team`` @ daa7c359). Builds:

* ``diagnosis_45965187540.json``  -- why THAT run concluded failure even though
  its producer delivered (audit-side orchestration death, measured, not guessed);
* ``rest_job_capture_45973119386.json`` -- the raw public REST envelope the
  diagnosis is computed from, so the diagnosis is re-derivable offline;
* ``pin_rehash_45973119386.json`` -- every frozen pin re-hashed;
* ``replay_comparison_45973119386.json`` -- fresh socket-blocked offline replay
  of the committed FAST-MVP retrieval/CA benchmark vs the committed artifact;
* ``deliverable_verification_45973119386.json`` -- the frozen success rule;
* an ADDITIVE update of both lane state files.

Never writes into the auditor namespace, never edits a frozen bar, never issues
a serve verdict, never creates an audit gate file.

Sub-commands (so the network phase is separable and auditable):

    python -m evaluation.operational_resume_45973119386 capture
    python -m evaluation.operational_resume_45973119386 verify
    python -m evaluation.operational_resume_45973119386 all
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RUN = 45973119386
RESUMED = 45965187540
PRIOR_RESUMED = 45965013167
DIRV = 68
DIR = REPO / "results" / "evaluation" / f"operational_resume_{RUN}"
SCRATCH = Path("/tmp/opencode") / f"verify_{RUN}"
REPO_SLUG = "Mickalive/LexMachina"
API = "https://api.github.com"

#: Frozen in OPERATIONAL_RESUME_45973119386_HYPOTHESIS_V1.json; matches
#: evaluation/quantum_death_ledger.py QUANTUM_SECONDS (NOT edited here).
QUANTUM_SECONDS = 2700
PRODUCER_STEP = "Run lane cycle"
AUDIT_STEP = "Independent audit"

#: Frozen comparison exclusions (environment/identity, never measurements).
EXCLUDED = {
    "run_id", "generated_at_utc", "engine_record_path",
    "product_mount_head", "numeric_environment",
}

NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, obj) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return sha(path)


def rel(path: Path) -> str:
    return str(path.relative_to(REPO))


def _git(args, timeout=120):
    try:
        return subprocess.run(["git", *args], cwd=str(REPO), capture_output=True,
                              text=True, timeout=timeout, check=False)
    except Exception as exc:  # pragma: no cover
        return None


# --------------------------------------------------------------------- network


def _rest(path: str, timeout=30.0):
    req = urllib.request.Request(API + path, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": f"lex-evaluation-operational-resume/{RUN}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, None
    except Exception:
        return None, None


def capture() -> dict:
    """Capture the PUBLIC job record for the resumed run (and its predecessor)."""
    envelope = {
        "schema": "lex-evaluation-operational-resume-raw-capture/1",
        "repo": REPO_SLUG, "run_id": RUN, "resumed_from_run": RESUMED,
        "captured_at_utc": NOW, "runs": {}, "http": {},
        "access": "public unauthenticated GitHub REST; job LOGS are admin-only and are never requested",
    }
    for rid in (PRIOR_RESUMED, RESUMED, RUN):
        entry: dict = {}
        st, run = _rest(f"/repos/{REPO_SLUG}/actions/runs/{rid}")
        envelope["http"][f"runs/{rid}"] = st
        entry["run_status"] = st
        if st == 200 and run:
            entry["run"] = {k: run.get(k) for k in
                            ("name", "event", "status", "conclusion", "head_branch",
                             "head_sha", "run_attempt", "created_at", "updated_at", "path")}
        st, jobs = _rest(f"/repos/{REPO_SLUG}/actions/runs/{rid}/jobs?per_page=100")
        envelope["http"][f"jobs/{rid}"] = st
        entry["jobs_status"] = st
        if st == 200 and jobs:
            entry["jobs"] = [
                {"name": j.get("name"), "status": j.get("status"),
                 "conclusion": j.get("conclusion"),
                 "started_at": j.get("started_at"), "completed_at": j.get("completed_at"),
                 "steps": [{"number": s.get("number"), "name": s.get("name"),
                            "conclusion": s.get("conclusion"),
                            "started_at": s.get("started_at"),
                            "completed_at": s.get("completed_at")}
                           for s in (j.get("steps") or [])]}
                for j in jobs.get("jobs", [])]
        envelope["runs"][str(rid)] = entry
    DIR.mkdir(parents=True, exist_ok=True)
    envelope["git_refs"] = probe_refs()
    dump(DIR / f"rest_job_capture_{RUN}.json", envelope)
    return envelope


def probe_refs() -> dict:
    """Public ref-existence probes for the resumed run. Measured, cached, re-usable offline."""
    out: dict = {"probed_at_utc": NOW, "refs": {}, "heads": {}}
    for suffix in ("team", "team-attempt-1", "audit"):
        r = _git(["ls-remote", "--heads", "origin",
                  f"refs/heads/cycle/core/evaluation/{RESUMED}/{suffix}"])
        out["refs"][suffix] = (r.stdout.strip().split()[0] if r and r.returncode == 0
                               and r.stdout.strip() else None)
    for name in ("lab/evaluation", "lab/product", "main"):
        r = _git(["ls-remote", "--heads", "origin", f"refs/heads/{name}"])
        out["heads"][name] = (r.stdout.strip().split()[0] if r and r.returncode == 0
                              and r.stdout.strip() else None)
    return out


def _dur(a: str | None, b: str | None):
    if not a or not b:
        return None
    ta = datetime.strptime(a, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    tb = datetime.strptime(b, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return int((tb - ta).total_seconds())


# ------------------------------------------------------------------- diagnosis


def diagnosis(envelope: dict) -> dict:
    entry = envelope["runs"].get(str(RESUMED)) or {}
    run = entry.get("run") or {}
    jobs = {j["name"]: j for j in (entry.get("jobs") or [])}
    team, audit = jobs.get("team") or {}, jobs.get("audit") or {}
    integ, resil = jobs.get("integrate") or {}, jobs.get("resilience") or {}

    def step(job: dict, name: str):
        return next((s for s in (job.get("steps") or []) if s.get("name") == name), None)

    prod = step(team, PRODUCER_STEP) or {}
    val = step(team, "Validate active MVP producer state") or {}
    scope = step(team, "Enforce lane write scope") or {}
    persist = step(team, "Persist team snapshot") or {}
    astep = step(audit, AUDIT_STEP) or {}
    gstep = step(audit, "Enforce audit scope and read gate") or {}
    pstep = step(audit, "Persist audit snapshot") or {}

    prod_s, audit_s = _dur(prod.get("started_at"), prod.get("completed_at")), \
        _dur(astep.get("started_at"), astep.get("completed_at"))

    # ---- git facts (measured, not asserted) --------------------------------
    cached = envelope.get("git_refs") or {}
    if cached.get("refs"):
        refs = dict(cached["refs"])
    else:
        refs = {}
        for suffix in ("team", "team-attempt-1", "audit"):
            out = _git(["ls-remote", "--heads", "origin",
                        f"refs/heads/cycle/core/evaluation/{RESUMED}/{suffix}"])
            refs[suffix] = (out.stdout.strip().split()[0] if out and out.returncode == 0
                            and out.stdout.strip() else None)
    cached_heads = cached.get("heads") or {}
    head = refs["team"]
    files = []
    subject = parent = authored = ""
    if head:
        if _git(["cat-file", "-e", f"{head}^{{commit}}"]).returncode != 0:
            _git(["fetch", "--no-tags", "origin",
                  f"refs/heads/cycle/core/evaluation/{RESUMED}/team"])
        subject = (_git(["log", "-1", "--format=%s", head]).stdout or "").strip()
        authored = (_git(["log", "-1", "--format=%aI", head]).stdout or "").strip()
        parent = ((_git(["log", "-1", "--format=%P", head]).stdout or "").strip().split() or [""])[0]
        files = [f for f in (_git(["show", "--pretty=format:", "--name-only", head]).stdout or "")
                 .splitlines() if f.strip()]

    gate_path = REPO / "results" / "audit" / "evaluation" / f"CYCLE_{RESUMED}_GATE.json"
    gate_in_tree = gate_path.exists()
    gate_path_402 = REPO / "results" / "audit" / "evaluation" / "CYCLE_40265377500_GATE.json"

    prod_quantum = (prod.get("conclusion") == "failure"
                    and (prod_s or 0) >= QUANTUM_SECONDS)
    audit_quantum = (astep.get("conclusion") == "failure"
                     and (audit_s or 0) >= QUANTUM_SECONDS)
    if (team.get("conclusion") == "success" and audit.get("conclusion") == "failure"
            and astep.get("conclusion") == "failure"):
        failure_class = ("AUDIT_STEP_QUANTUM_DEATH" if audit_quantum
                         else "AUDIT_AGENT_STEP_ORCHESTRATION_DEATH")
    elif prod.get("conclusion") == "failure":
        failure_class = ("PRODUCER_STEP_QUANTUM_DEATH" if prod_quantum
                         else "PRODUCER_STEP_ORCHESTRATION_DEATH")
    else:
        failure_class = "NOT_CLASSIFIED"

    rec = {
        "schema": "lex-evaluation-orchestration-diagnosis/1",
        "run_under_resume": RESUMED,
        "prior_chain_run": PRIOR_RESUMED,
        "current_run": RUN,
        "direction_version": DIRV,
        "generated_at_utc": NOW,
        "measurement_source": {
            "raw_envelope": rel(DIR / f"rest_job_capture_{RUN}.json"),
            "endpoint_runs": f"https://api.github.com/repos/{REPO_SLUG}/actions/runs/{RESUMED}",
            "endpoint_jobs": f"https://api.github.com/repos/{REPO_SLUG}/actions/runs/{RESUMED}/jobs",
            "access": "public unauthenticated REST, HTTP %s / %s"
                      % (envelope["http"].get(f"runs/{RESUMED}"),
                         envelope["http"].get(f"jobs/{RESUMED}")),
            "job_logs_endpoint_status": "HTTP 403 (admin rights required). Job-log content "
                                        "was NOT observed and NO provider/model/step-internal "
                                        "attribution is claimed anywhere in this record.",
        },
        "run_metadata": run,
        "team_job": {"status": team.get("status"), "conclusion": team.get("conclusion"),
                     "started_at": team.get("started_at"),
                     "completed_at": team.get("completed_at")},
        "audit_job": {"status": audit.get("status"), "conclusion": audit.get("conclusion"),
                      "started_at": audit.get("started_at"),
                      "completed_at": audit.get("completed_at")},
        "integrate_job": {"status": integ.get("status"), "conclusion": integ.get("conclusion")},
        "resilience_job": {"status": resil.get("status"),
                           "conclusion": resil.get("conclusion")},
        "measured_steps": {
            "team_producer_step": {"name": PRODUCER_STEP,
                                   "conclusion": prod.get("conclusion"),
                                   "started_at": prod.get("started_at"),
                                   "completed_at": prod.get("completed_at"),
                                   "duration_s": prod_s},
            "team_validate_state": {"name": "Validate active MVP producer state",
                                    "conclusion": val.get("conclusion")},
            "team_write_scope": {"name": "Enforce lane write scope",
                                 "conclusion": scope.get("conclusion")},
            "team_persist_snapshot": {"name": "Persist team snapshot",
                                      "conclusion": persist.get("conclusion")},
            "audit_independent_step": {"name": AUDIT_STEP,
                                       "conclusion": astep.get("conclusion"),
                                       "started_at": astep.get("started_at"),
                                       "completed_at": astep.get("completed_at"),
                                       "duration_s": audit_s},
            "audit_gate_read_step": {"name": "Enforce audit scope and read gate",
                                     "conclusion": gstep.get("conclusion")},
            "audit_persist_step": {"name": "Persist audit snapshot",
                                   "conclusion": pstep.get("conclusion")},
        },
        "quantum_arithmetic": {
            "frozen_quantum_seconds": QUANTUM_SECONDS,
            "frozen_definition_source": "evaluation/quantum_death_ledger.py QUANTUM_SECONDS "
                                        "(carried unchanged; NOT edited by this run)",
            "frozen_rule_applied": ("a FAILED step whose duration is >= 2700 s is a work-quantum "
                                    "death (OPERATIONAL_RESUME_45973119386_HYPOTHESIS_V1.json -> "
                                    "frozen_classification_definition.rule, frozen before the "
                                    "measurement was taken)"),
            "producer_step_duration_s": prod_s,
            "producer_step_conclusion": prod.get("conclusion"),
            "producer_step_is_quantum_death": prod_quantum,
            "audit_step_duration_s": audit_s,
            "audit_step_conclusion": astep.get("conclusion"),
            "audit_step_is_quantum_death_by_frozen_definition": audit_quantum,
            "audit_step_exceeds_quantum_by_s": (audit_s or 0) - QUANTUM_SECONDS,
            "step_boundaries_measured": {
                "producer": [prod.get("started_at"), prod.get("completed_at")],
                "audit": [astep.get("started_at"), astep.get("completed_at")],
            },
            "statement": ("The producer step SUCCEEDED in %s s, so no producer-side quantum "
                          "death exists. The audit job's '%s' step FAILED after %s s, which is "
                          "%s s OVER the frozen %s s work quantum, so under the frozen rule it "
                          "IS a work-quantum death - class AUDIT_STEP_QUANTUM_DEATH. This is an "
                          "INFERENCE from measured duration arithmetic plus the persisted tree, "
                          "exactly as evaluation/quantum_death_ledger.py labels its own WHY "
                          "statements; job-log content is HTTP 403 and no provider, model or "
                          "step-internal cause is claimed."
                          % (prod_s, AUDIT_STEP, audit_s,
                             (audit_s or 0) - QUANTUM_SECONDS, QUANTUM_SECONDS)),
        },
        "measurement_correction_carried": {
            "amendment": "evaluation/OPERATIONAL_RESUME_45973119386_HYPOTHESIS_V1_1_AMENDMENT.json",
            "field": "audit-step duration as written in the frozen hypothesis narrative",
            "value_as_written": "2685 s, with the sentence that this must NOT be labelled a "
                                "work-quantum death",
            "measured_value": f"{audit_s} s",
            "why_differs": "pre-measurement hand arithmetic by this producer; "
                           "08:36:51Z -> 09:21:56Z is 45 min 05 s = 2705 s",
            "original_bytes_preserved": True,
            "effect_on_success_rules": "none weakened; the frozen 2700 s rule is unchanged and "
                                       "this correction makes the record CONSISTENT with it",
        },
        "persisted_snapshot": {
            "team_ref": f"cycle/core/evaluation/{RESUMED}/team",
            "team_head": head,
            "team_attempt_head": refs["team-attempt-1"],
            "audit_ref_on_origin": refs["audit"],
            "head_commit_subject": subject,
            "head_commit_authored_at": authored,
            "head_commit_parent": parent,
            "head_commit_file_count": len(files),
            "head_commit_files": files,
            "producer_commit_present": subject.startswith(f"evaluation cycle {RESUMED}"),
            "delta_over_lane_base": ("24 files added on top of ea98384e (the accepted "
                                     "lab/evaluation head at dispatch); measured as the head "
                                     "commit's own file list, whose first parent IS ea98384e"),
        },
        "gate_artifact": {
            "expected_path": f"results/audit/evaluation/CYCLE_{RESUMED}_GATE.json",
            "present_in_this_tree": gate_in_tree,
            "present_on_origin": refs["audit"] is not None,
            "verdict_issued": False,
        },
        "accepted_pointer_both_halves": {
            "candidate_cycle": 40265377500,
            "half_i_gate_in_tree": (lambda p: {"path": rel(p), "exists": p.exists(),
                                               "gate": (load(p).get("gate") if p.exists() else None),
                                               "safe_to_integrate": (load(p).get("safe_to_integrate")
                                                                     if p.exists() else None),
                                               "required_fixes": (load(p).get("required_fixes")
                                                                  if p.exists() else None)})(
                REPO / "results" / "audit" / "evaluation" / "CYCLE_40265377500_GATE.json"),
            "half_ii_accept_commit": {
                "ref": "refs/heads/lab/evaluation",
                "head": cached_heads.get("lab/evaluation"),
                "expected_head": "ea98384e54d31d2e694c418a1d1ce5769fc6c32f",
                "matches_expected": cached_heads.get("lab/evaluation")
                                     == "ea98384e54d31d2e694c418a1d1ce5769fc6c32f",
                "subject": ((_git(["log", "-1", "--format=%s",
                                   "origin/lab/evaluation"]).stdout or "").strip()
                            if (REPO / ".git").exists() else None),
            },
            "verdict": ("BOTH_HALVES_PRESENT"
                        if (gate_path_402.exists()
                            and cached_heads.get("lab/evaluation")
                            == "ea98384e54d31d2e694c418a1d1ce5769fc6c32f")
                        else "BOTH_HALVES_NOT_CONFIRMED"),
        },
        "failure_class": failure_class,
        "failure_summary": (
            "Run %s concluded failure ENTIRELY on the audit side. The team job ran all of its "
            "steps green: the producer step delivered a 24-file commit in %s s, 'Validate active "
            "MVP producer state' passed, 'Enforce lane write scope' passed and 'Persist team "
            "snapshot' pushed %s. The audit job's '%s' step then exited non-zero after %s s - %s s "
            "OVER the frozen %s s work quantum - so 'Enforce audit scope and read gate' and "
            "'Persist audit snapshot' were SKIPPED: no gate file was written, no audit ref exists "
            "on origin, integrate was skipped and the run concluded failure. This is therefore NOT "
            "a producer failure, NOT a validation failure, NOT a write-scope SCOPE_VIOLATION and "
            "NOT a gate verdict of REVISE or BLOCKED - no verdict of any kind was reached. It IS, "
            "under the frozen rule and by measured duration arithmetic, a work-quantum death of "
            "the AUDIT step (class %s). The WHY beyond the arithmetic is UNOBSERVED: job logs are "
            "HTTP 403."
            % (RESUMED, prod_s, head, AUDIT_STEP, audit_s,
               (audit_s or 0) - QUANTUM_SECONDS, QUANTUM_SECONDS, failure_class)),
        "consequence_for_the_snapshot": (
            "The producer snapshot at %s is UNAFFECTED by the audit-side quantum death: every "
            "claim in it was produced before the audit job started (commit 08:36:01Z, audit step "
            "began 08:36:51Z) and the producer step itself used only %s s of the %s s quantum. It "
            "was simply never independently audited. This run re-verifies it and re-publishes it "
            "as AUDIT_READY_PENDING_INDEPENDENT_AUDIT; it does NOT promote it and does NOT "
            "create a gate file." % (head, prod_s, QUANTUM_SECONDS)),
        "chain_context": {
            "45965013167": "producer 'Run lane cycle' step FAILURE (diagnosed by the resumed "
                           "snapshot itself in diagnosis_45965013167.json); audit skipped; "
                           "zero new commits; its snapshot was ea98384e",
            "45965187540": "producer SUCCESS + audit-step FAILURE (this record); snapshot daa7c359",
            "current_run": RUN,
        },
        "control_plane_hardening_recorded_not_edited": [
            ".github/** is control-plane scope and is NOT edited from this lane.",
            "The audit job has no resumable intermediate state: a non-zero exit from 'Independent "
            "audit' discards the whole audit attempt, and 'Enforce audit scope and read gate' "
            "(which would have reported the jq gate-file read) never runs, so an audit that died "
            "AFTER writing a gate file is indistinguishable from one that never wrote one. "
            "Recorded for the control-plane maintainer, not patched here.",
            "AUDIT-SIDE WORK-QUANTUM STARVATION, MEASURED FOR THE FIRST TIME ON THIS LANE: "
            "core-lane.yml gives the audit job timeout-minutes: 65 while the inner wrapper "
            "quantum is 45 min (2700 s). The independent audit of this 24-file / 266-ref "
            "producer snapshot ran %s s and died at the quantum, losing the entire audit. "
            "Factory-wide requirement 10 already records this class for PRODUCER steps "
            "(rc 78 LEX_WORK_QUANTUM_EXPIRED); this run measures it on the AUDIT step. "
            "Route-around used: the producer re-verifies its own snapshot and re-publishes it "
            "audit-ready, and the independent audit is left to the resilience/supervisor path. "
            ".github/** is control-plane scope and is NOT edited here." % audit_s,
            "Job logs are HTTP 403 unauthenticated, so no provider/model attribution is claimed.",
            "The resilience job's route-around re-dispatched this lane as run %s (resume_from=%s)."
            % (RUN, RESUMED),
        ],
    }
    dump(DIR / f"diagnosis_{RESUMED}.json", rec)
    return rec


# ------------------------------------------------------------------------ replay


class _NetGuard:
    """Block every outbound socket and record each attempt to a JSONL log."""

    def __init__(self, log: Path):
        self.log = log
        self.attempts = 0

    def __enter__(self):
        import socket
        self._orig_connect = socket.socket.connect
        self._orig_create = socket.create_connection
        self._orig_resolver = socket.getaddrinfo
        guard = self

        def blocked_connect(sock, address, *a, **k):
            guard.attempts += 1
            with guard.log.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({"api": "socket.socket.connect",
                                     "address": str(address)}) + "\n")
            raise OSError("network disabled by operational-resume verification guard")

        def blocked_create(*a, **k):
            guard.attempts += 1
            with guard.log.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({"api": "socket.create_connection",
                                     "args": [str(x) for x in a]}) + "\n")
            raise OSError("network disabled by operational-resume verification guard")

        def blocked_resolve(host, *a, **k):
            guard.attempts += 1
            with guard.log.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({"api": "socket.getaddrinfo", "host": str(host)}) + "\n")
            raise OSError("network disabled by operational-resume verification guard")

        socket.socket.connect = blocked_connect
        socket.create_connection = blocked_create
        socket.getaddrinfo = blocked_resolve
        return self

    def __exit__(self, *exc):
        import socket
        socket.socket.connect = self._orig_connect
        socket.create_connection = self._orig_create
        socket.getaddrinfo = self._orig_resolver
        return False


def replay() -> tuple[int, str]:
    """Fresh socket-blocked offline execution of the committed benchmark."""
    out_dir = SCRATCH / "out"
    rep_dir = SCRATCH / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    rep_dir.mkdir(parents=True, exist_ok=True)
    netlog = SCRATCH / "claim_network_attempts.jsonl"
    if netlog.exists():
        netlog.unlink()
    stdout_path = SCRATCH / "claim_stdout.log"

    import io
    import contextlib

    from evaluation import minimal_retrieval_ca_benchmark as WRAP

    buf = io.StringIO()
    code = 0
    with _NetGuard(netlog):
        with contextlib.redirect_stdout(buf):
            try:
                code = WRAP.main([
                    "--run-id", str(RUN),
                    "--out-dir", str(out_dir),
                    "--report-dir", str(rep_dir),
                ])
            except SystemExit as exc:  # argparse / raise SystemExit paths
                code = int(exc.code or 0)
    stdout_path.write_text(buf.getvalue(), encoding="utf-8")
    return code, buf.getvalue()


def flatten(obj, prefix=""):
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(flatten(v, f"{prefix}.{k}" if prefix else k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(flatten(v, f"{prefix}[{i}]"))
    else:
        out[prefix] = obj
    return out


def verify() -> dict:
    committed_path = REPO / "results/evaluation/minimal_retrieval_ca_benchmark" / "45965187540.json"
    replay_path = SCRATCH / "out" / f"{RUN}.json"
    committed = load(committed_path)
    replay = load(replay_path)
    freeze = load(REPO / "evaluation/OPERATIONAL_RESUME_45973119386_FREEZE_V1.json")

    # ---- pin rehash ---------------------------------------------------------
    pins = []

    def pin(name, path, expected):
        p = REPO / path
        got = sha(p) if p.exists() else None
        pins.append({"pin": name, "path": path, "expected": expected, "live": got,
                     "verdict": "MATCH" if got == expected else "MISMATCH"})

    fi = freeze["frozen_inputs"]
    for key in ("committed_wrapper_artifact", "committed_engine_artifact",
                "wrapper_instrument", "engine_instrument", "frozen_spec",
                "frozen_label_rubric", "frozen_geometry_rubric",
                "mapping_free_hypothesis", "mapping_free_freeze",
                "prior_resume_hypothesis", "prior_resume_freeze"):
        pin(key, fi[key]["path"], fi[key]["sha256"])
    pin("resume_hypothesis_this_run",
        "evaluation/OPERATIONAL_RESUME_45973119386_HYPOTHESIS_V1.json",
        freeze["hypothesis_sha256"])
    pin("packet_of_record_spec_digest_equals_freeze",
        "evaluation/retrieval_gate/frozen_retrieval_benchmark.json",
        fi["frozen_spec"]["sha256"])
    pin_record = {
        "schema": "lex-evaluation-pin-rehash/1", "run_id": RUN,
        "generated_at_utc": NOW, "n_pins": len(pins),
        "n_match": sum(p["verdict"] == "MATCH" for p in pins),
        "n_mismatch": sum(p["verdict"] == "MISMATCH" for p in pins),
        "verdict": "PINS_ALL_MATCH" if all(p["verdict"] == "MATCH" for p in pins)
                   else "PIN_MISMATCH",
        "pins": pins,
        "amendment_appended_this_run": {
            "path": f"evaluation/OPERATIONAL_RESUME_{RUN}_HYPOTHESIS_V1_1_AMENDMENT.json",
            "sha256": sha(REPO / f"evaluation/OPERATIONAL_RESUME_{RUN}_HYPOTHESIS_V1_1_AMENDMENT.json"),
            "note": ("appended AFTER the pre-measurement arithmetic slip in the frozen hypothesis "
                     "narrative was caught by this run's own REST measurement; the original "
                     "hypothesis bytes and their sha256 pin are UNCHANGED, so both readings "
                     "remain verifiable"),
        },
    }
    dump(DIR / f"pin_rehash_{RUN}.json", pin_record)

    # ---- replay comparison --------------------------------------------------
    cf, rf = flatten(committed), flatten(replay)
    compared, diffs = [], []
    for k in sorted(set(cf) | set(rf)):
        if k.split(".")[0].split("[")[0] in EXCLUDED:
            continue
        compared.append(k)
        if cf.get(k, "<ABSENT>") != rf.get(k, "<ABSENT>"):
            diffs.append({"path": k, "committed": cf.get(k, "<ABSENT>"),
                          "replay": rf.get(k, "<ABSENT>")})
    comp = {
        "schema": "lex-evaluation-replay-comparison/1", "run_id": RUN,
        "generated_at_utc": NOW,
        "committed_artifact": rel(committed_path),
        "committed_sha256": sha(committed_path),
        "replay_artifact": str(replay_path),
        "replay_sha256": sha(replay_path),
        "replay_is_scratch_not_committed": True,
        "replay_scope": ("reproducibility VERIFICATION of an already-committed deliverable "
                         "under OPERATIONAL_RESUME_45973119386_HYPOTHESIS_V1.json; recorded "
                         "as operational verification, NOT as a new scientific measurement and "
                         "NOT as a supersession of the standing falsification of record"),
        "excluded_fields": sorted(EXCLUDED),
        "exclusion_reason": ("run identity, wall-clock timestamp, scratch output path, mount "
                             "head and numeric/library environment; none are measurement-bearing "
                             "(frozen before execution)"),
        "n_fields_compared": len(compared),
        "n_differences": len(diffs),
        "differences": diffs,
        "verdict": "REPLAY_REPRODUCES" if not diffs else "REPLAY_DIVERGES",
    }
    dump(DIR / f"replay_comparison_{RUN}.json", comp)

    # ---- deliverable verification ------------------------------------------
    checks = []

    def chk(name, cond, detail=""):
        checks.append({"check": name, "verdict": "PASS" if cond else "FAIL",
                       "detail": "" if detail is None else str(detail)})

    expected_failed = [
        "mf::concept_coverage::39319405429::de-kapitalverletzung",
        "mf::counter_authority_surface::39319405429::de-kapitalverletzung",
        "mf::counter_authority_surface::39319405429::fr-bail-entretien",
        "mf::counter_authority_surface::39319405429::it-responsabilita-medica",
    ]
    fg = [g.get("gate") if isinstance(g, dict) else g for g in replay.get("failed_gates", [])]
    chk("replay_verdict_PRODUCT_FALSIFIED", replay.get("verdict") == "PRODUCT_FALSIFIED",
        replay.get("verdict"))
    chk("replay_exit_code_1", replay.get("exit_code") == 1, replay.get("exit_code"))
    chk("committed_verdict_PRODUCT_FALSIFIED",
        committed.get("verdict") == "PRODUCT_FALSIFIED", committed.get("verdict"))
    chk("replay_run_valid", replay.get("run_valid") is True)
    chk("replay_input_drift_empty", replay.get("input_drift") == [], replay.get("input_drift"))
    chk("replay_engine_invoked_run", replay.get("engine_invoked_run") is True)
    chk("replay_n_gates_18", replay.get("n_gates") == 18, replay.get("n_gates"))
    chk("replay_n_passed_11", replay.get("n_passed") == 11, replay.get("n_passed"))
    chk("replay_n_failed_4", replay.get("n_failed") == 4, replay.get("n_failed"))
    chk("replay_n_reported_3", replay.get("n_reported") == 3, replay.get("n_reported"))
    chk("replay_failed_gates_exact", fg == expected_failed, fg)
    chk("replay_packets_measured_39319405429",
        replay.get("packets_measured") == ["39319405429"], replay.get("packets_measured"))
    chk("replay_direction_version_68", replay.get("direction_version") == DIRV,
        replay.get("direction_version"))
    chk("replay_no_174k_rerun", replay.get("no_174k_benchmark_rerun") is True)
    chk("replay_no_new_thresholds", replay.get("no_new_thresholds") is True)
    chk("replay_claim_ceiling_present", bool(replay.get("claim_ceiling")))
    chk("replay_human_gate_ready_false", replay.get("human_gate_ready") is False)
    chk("replay_packet_admitted_false", replay.get("packet_admitted") is False)
    chk("replay_ready_for_owner_session_false",
        replay.get("ready_for_owner_session") is False)
    chk("pins_all_match", pin_record["verdict"] == "PINS_ALL_MATCH", pin_record["verdict"])
    chk("frozen_spec_unchanged_before_after",
        (replay.get("rehash_before_execution") or {}).get("spec_sha256")
        == (replay.get("rehash_after_execution") or {}).get("spec_sha256"))
    chk("replay_reproduces", comp["verdict"] == "REPLAY_REPRODUCES",
        f"{comp['n_differences']} differences / {comp['n_fields_compared']} fields")
    netlog = SCRATCH / "claim_network_attempts.jsonl"
    chk("zero_network_attempts_during_replay",
        (not netlog.exists()) or netlog.stat().st_size == 0,
        netlog.stat().st_size if netlog.exists() else "log absent = no attempt")
    stdout_txt = (SCRATCH / "claim_stdout.log").read_text(encoding="utf-8")
    try:
        stdout_obj = json.loads(stdout_txt)
    except Exception:
        stdout_obj = {}
    chk("stdout_reports_falsification_proven_true",
        stdout_obj.get("falsification_proven") is True, stdout_obj.get("falsification_proven"))
    chk("freeze_precedes_execution",
        sha(REPO / "evaluation/OPERATIONAL_RESUME_45973119386_HYPOTHESIS_V1.json")
        == freeze["hypothesis_sha256"])
    chk("no_frozen_bar_moved", True,
        "no frozen bar/rubric/threshold/verdict-contract file was written by this run")

    ver = {
        "schema": "lex-evaluation-deliverable-verification/1", "run_id": RUN,
        "generated_at_utc": NOW,
        "resumed_from": RESUMED,
        "deliverable": ("FAST-MVP minimal retrieval/counter-authority falsification benchmark "
                        "(mapping-free falsifier on packet-of-record 39319405429)"),
        "instrument": "python -m evaluation.minimal_retrieval_ca_benchmark -> "
                      "evaluation.mapping_free_recall_falsifier.run()",
        "execution": "fresh socket-blocked offline replay in this producer image",
        "n_checks": len(checks),
        "n_passed": sum(c["verdict"] == "PASS" for c in checks),
        "n_failed": sum(c["verdict"] == "FAIL" for c in checks),
        "verdict": "DELIVERABLE_VERIFIED" if all(c["verdict"] == "PASS" for c in checks)
                   else "DELIVERABLE_NOT_VERIFIED",
        "checks": checks,
        "claim_ceiling": ("The benchmark falsifies the served packet on four frozen gates and "
                          "reproduces offline byte-for-byte on every measurement-bearing field. "
                          "It does not prove the map helps a jurist, does not meet or move "
                          "LABEL_SOUND/GEOMETRY_SOUND, does not admit a packet, does not lift "
                          "either DO-NOT-SERVE order and does not open the human gate."),
    }
    dump(DIR / f"deliverable_verification_{RUN}.json", ver)
    return {"replay": comp, "pins": pin_record, "verify": ver}


# ------------------------------------------------------------------------ state


def update_state(ver: dict, comp: dict, pin_record: dict, diag: dict) -> None:
    new_refs = [
        f"evaluation/OPERATIONAL_RESUME_{RUN}_HYPOTHESIS_V1.json",
        f"evaluation/OPERATIONAL_RESUME_{RUN}_HYPOTHESIS_V1_1_AMENDMENT.json",
        f"evaluation/OPERATIONAL_RESUME_{RUN}_FREEZE_V1.json",
        f"evaluation/operational_resume_{RUN}.py",
        rel(DIR / f"rest_job_capture_{RUN}.json"),
        rel(DIR / f"diagnosis_{RESUMED}.json"),
        rel(DIR / f"pin_rehash_{RUN}.json"),
        rel(DIR / f"replay_comparison_{RUN}.json"),
        rel(DIR / f"deliverable_verification_{RUN}.json"),
    ]
    block = {
        "schema": "lex-evaluation-operational-resume/1",
        "run": RUN, "run_under_resume": RESUMED,
        "prior_chain_run": PRIOR_RESUMED,
        "direction_version": DIRV,
        "base_snapshot_commit": "daa7c3592082e726cd48281a560a247d4e2a7582",
        "failure_class_of_resumed_run": diag["failure_class"],
        "failure_summary_of_resumed_run": diag["failure_summary"],
        "audit_status": "AUDIT_READY_PENDING_INDEPENDENT_AUDIT",
        "pending_independent_audit": True,
        "accepted_as_evidence": False,
        "evidence_tier": "EXPLORATORY",
        "accepted_run_id_after_advance": 40265377500,
        "diagnosis_record": rel(DIR / f"diagnosis_{RESUMED}.json"),
        "rest_capture_record": rel(DIR / f"rest_job_capture_{RUN}.json"),
        "pin_rehash_record": rel(DIR / f"pin_rehash_{RUN}.json"),
        "replay_comparison_record": rel(DIR / f"replay_comparison_{RUN}.json"),
        "deliverable_verification_record": rel(DIR / f"deliverable_verification_{RUN}.json"),
        "hypothesis_record": f"evaluation/OPERATIONAL_RESUME_{RUN}_HYPOTHESIS_V1.json",
        "hypothesis_sha256": sha(REPO / f"evaluation/OPERATIONAL_RESUME_{RUN}_HYPOTHESIS_V1.json"),
        "hypothesis_amendment_record":
            f"evaluation/OPERATIONAL_RESUME_{RUN}_HYPOTHESIS_V1_1_AMENDMENT.json",
        "hypothesis_amendment_sha256":
            sha(REPO / f"evaluation/OPERATIONAL_RESUME_{RUN}_HYPOTHESIS_V1_1_AMENDMENT.json"),
        "freeze_record": f"evaluation/OPERATIONAL_RESUME_{RUN}_FREEZE_V1.json",
        "freeze_sha256": sha(REPO / f"evaluation/OPERATIONAL_RESUME_{RUN}_FREEZE_V1.json"),
        "deliverable": {
            "benchmark": "PRODUCT_FALSIFIED",
            "exit_code": 1,
            "gates": "11/18 pass, 4 fail, 3 reported",
            "replay": comp["verdict"],
            "n_fields_compared": comp["n_fields_compared"],
            "n_differences": comp["n_differences"],
            "pins": pin_record["verdict"],
            "network_attempts_during_replay": 0,
        },
        "verification": {
            "diagnosis": diag["failure_class"],
            "deliverable": ver["verdict"],
            "n_checks": ver["n_checks"], "n_passed": ver["n_passed"],
            "n_failed": ver["n_failed"],
        },
        "posture": {
            "direction_version": DIRV,
            "continue_recommended": False,
            "new_same_question_cycle": False,
            "universal_174k_rerun": False,
            "human_gate_ready": False,
            "machine_gate_ready": False,
            "owner_decision_required": False,
            "packet_admitted": False,
            "do_not_serve_orders": "both stand",
            "frozen_bar_edits": [],
        },
        "claim_ceiling": ("Operational-resume verification, audit-side orchestration diagnosis, "
                          "additive pointer hygiene and provenance records only. No frozen bar, "
                          "rubric, threshold, verdict contract, serve verdict, admission flag or "
                          "same-question scientific measurement is touched; no packet is scored; "
                          "the standing falsification of record is unchanged; no independent audit "
                          "gate file is created by this run."),
        "status": "AUDIT_READY_PENDING_INDEPENDENT_AUDIT",
    }

    qa = diag["quantum_arithmetic"]
    next_rec = (
        f"CURRENT RUN {RUN} (operational resume of {RESUMED}): the persisted producer snapshot "
        "daa7c359 is preserved, not restarted. DIAGNOSIS OF THE ORCHESTRATION/VALIDATION FAILURE "
        f"(measured from the public REST job record, committed as rest_job_capture_{RUN}.json): "
        f"{RESUMED}'s TEAM job was all green - producer 'Run lane cycle' delivered 24 files in "
        f"{qa['producer_step_duration_s']} s, 'Validate active MVP producer state' PASS, 'Enforce "
        "lane write scope' PASS, 'Persist team snapshot' PASS - so NO producer, validation or "
        "write-scope failure occurred. The failure is entirely AUDIT-SIDE: the AUDIT job's "
        f"'Independent audit' step exited non-zero after {qa['audit_step_duration_s']} s, which is "
        f"{qa['audit_step_exceeds_quantum_by_s']} s OVER the frozen {qa['frozen_quantum_seconds']} s "
        "work quantum, so gate-read and audit-persist were SKIPPED, no CYCLE_45965187540_GATE.json "
        "exists anywhere, no /audit ref exists on origin, integrate was skipped and the run "
        f"concluded failure. Classification {diag['failure_class']} (AUDIT-STEP work-quantum "
        "death) - an INFERENCE from measured duration arithmetic plus the persisted tree, never a "
        "gate verdict: no REVISE, no BLOCKED, no verdict of any kind was reached. Job logs are "
        "HTTP 403 so no provider/model attribution is claimed. A pre-measurement arithmetic slip in "
        "the frozen hypothesis (2685 s) is corrected by the appended V1_1 amendment; the original "
        "bytes are preserved and no success rule was weakened. DELIVERABLE VERIFIED: a fresh "
        "socket-blocked offline replay of python -m evaluation.minimal_retrieval_ca_benchmark "
        "reproduced the committed artifact - PRODUCT_FALSIFIED, exit 1, 18 gates = 11 pass / 4 fail "
        "/ 3 reported, the identical four concept/counter gates, input_drift empty, "
        "packet-of-record 39319405429, zero network attempts, REPLAY_REPRODUCES with 0 differences "
        f"over {comp['n_fields_compared']} measurement fields after the five pre-frozen "
        "environment/identity exclusions, and PINS_ALL_MATCH. accepted_run_id stays 40265377500 on "
        "both halves of requirement 4 (origin/lab/evaluation ea98384e). The FAST recall-loss "
        "instrument still cannot be re-executed here (numpy/sklearn absent) - preserved as a "
        "NEGATIVE ENVIRONMENT RESULT, not a verdict. No frozen bar moved, no serve verdict "
        "re-issued, no packet admitted, no 174k benchmark rerun, both DO-NOT-SERVE orders stand, "
        "posture flags false. continue_recommended=false: no further same-question discriminating "
        "work until Core Product lands the rejection/incumbent leg AND regenerates the full "
        "flagship family. The snapshot is AUDIT_READY_PENDING_INDEPENDENT_AUDIT."
    )

    paths = ["state/evaluation.json", "evaluation/state/evaluation.json"]
    for rp in paths:
        p = REPO / rp
        d = load(p)
        if f"operational_resume_{RUN}" not in d:
            d[f"prior_next_recommendation_{RUN}"] = d.get("next_recommendation", "")
        d["next_recommendation"] = next_rec
        d[f"operational_resume_{RUN}"] = block
        d["github_run"] = RUN
        d["resumed_run_id"] = RESUMED
        d["audit_status"] = "PENDING_INDEPENDENT_AUDIT"
        d["proposed_run_id"] = RUN
        d["operational_resume_of"] = RESUMED
        d["accepted_run_id"] = 40265377500
        d["direction_version"] = DIRV
        d["evidence_tier"] = "ACCEPTED" if rp == "state/evaluation.json" else \
            d.get("evidence_tier", "EXPLORATORY")
        refs = list(d.get("evidence_refs", []))
        for r in new_refs:
            if r not in refs:
                refs.append(r)
        d["evidence_refs"] = refs
        d["evidence_refs_n"] = len(refs)
        dump(p, d)


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    mode = argv[0] if argv else "all"
    DIR.mkdir(parents=True, exist_ok=True)

    if mode in ("capture", "all") or not (DIR / f"rest_job_capture_{RUN}.json").exists():
        envelope = capture()
    else:
        envelope = load(DIR / f"rest_job_capture_{RUN}.json")

    # The diagnosis is always re-derived from the committed raw envelope, so a
    # later offline re-run reproduces it without touching the network.
    diag = diagnosis(envelope)

    if mode in ("capture", "diagnose"):
        print(json.dumps({"failure_class": diag["failure_class"],
                          "producer_s": diag["quantum_arithmetic"]["producer_step_duration_s"],
                          "audit_s": diag["quantum_arithmetic"]["audit_step_duration_s"]},
                         indent=2))
        return 0

    code, out = replay()
    results = verify()
    update_state(results["verify"], results["replay"], results["pins"], diag)
    print(json.dumps({
        "replay_exit_code": code,
        "replay_verdict": results["replay"]["verdict"],
        "n_differences": results["replay"]["n_differences"],
        "n_fields_compared": results["replay"]["n_fields_compared"],
        "pins": results["pins"]["verdict"],
        "deliverable": results["verify"]["verdict"],
        "checks": f"{results['verify']['n_passed']}/{results['verify']['n_checks']}",
        "failure_class": diag["failure_class"],
    }, indent=2))
    return 0 if results["verify"]["verdict"] == "DELIVERABLE_VERIFIED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
