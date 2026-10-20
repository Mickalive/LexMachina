#!/usr/bin/env python3
"""Live, machine-established evidence for the two orchestration failures this
OPERATIONAL RESUME (run 39381093325) was dispatched to repair.

  * subject run   39380758180  - team step "Run lane cycle" failed, exit 67
    LEX_ZERO_DELTA_REPAIR (zero durable delta, HEAD identical to the resume
    base snapshot 5a3c0eb8); audit/integrate never ran.
  * producer run  39379766198  - team job SUCCESS, but the audit job step
    "Enforce audit scope and read gate" failed, exit 3, annotation
    'auditor crossed scope:'; the exact out-of-scope paths are NOT in the
    annotation and the job-log zip endpoint answers HTTP 403 to an
    unauthenticated client, so those paths stay UNDETERMINED (bounded), never
    guessed.  "Persist audit snapshot" and "integrate" were skipped, so no
    /audit ref and no gate file exist for 39379766198.

Evidence source: GitHub REST API (public repo, unauthenticated) at execution
time - /actions/runs/<id>, /actions/runs/<id>/jobs, /check-runs/<job_id>/
annotations.  If the API is unreachable the instrument emits the pinned
fallback values captured at 2026-10-20T06:5xZ and DISCLOSES the fallback
rather than inventing live evidence.  No Product code is imported.  Nothing
is written outside --out.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RUN_ID = "39381093325"
API = "https://api.github.com/repos/Mickalive/LexMachina"
SNAPSHOT_BASE = "5a3c0eb8"

# Pinned fallback (captured 2026-10-20T06:5xZ, unauthenticated REST):
PINNED = {
    "39380758180": {
        "name": "Core evaluation dirV60 repair0",
        "conclusion": "failure",
        "event": "workflow_dispatch",
        "head_sha": "be84cc59388180e4a0aadd920f5cbe4725bbfeb2",
        "created_at": "2026-10-20T06:30:27Z",
        "updated_at": "2026-10-20T06:33:51Z",
        "jobs": [
            {"id": 118489119764, "name": "team", "conclusion": "failure",
             "failing_steps": ["Run lane cycle"],
             "annotations": [
                 {"level": "failure", "message": "Process completed with exit code 67."},
                 {"level": "failure", "message": "LEX_ZERO_DELTA_REPAIR"},
             ]},
            {"id": 118490092548, "name": "resilience", "conclusion": "success",
             "failing_steps": [], "annotations": []},
            {"id": 118490092764, "name": "audit", "conclusion": "skipped",
             "failing_steps": [], "annotations": []},
            {"id": 118490094065, "name": "integrate", "conclusion": "skipped",
             "failing_steps": [], "annotations": []},
        ],
    },
    "39379766198": {
        "name": "Core evaluation dirV60 repair0",
        "conclusion": "failure",
        "event": "workflow_dispatch",
        "head_sha": "be84cc59388180e4a0aadd920f5cbe4725bbfeb2",
        "created_at": "2026-10-20T06:20:05Z",
        "updated_at": "2026-10-20T06:30:32Z",
        "jobs": [
            {"id": 118485957281, "name": "team", "conclusion": "success",
             "failing_steps": [], "annotations": []},
            {"id": 118488190059, "name": "audit", "conclusion": "failure",
             "failing_steps": ["Enforce audit scope and read gate"],
             "annotations": [
                 {"level": "failure", "message": "Process completed with exit code 3."},
                 {"level": "failure", "message": "auditor crossed scope:"},
             ]},
            {"id": 118489043770, "name": "resilience", "conclusion": "success",
             "failing_steps": [], "annotations": []},
            {"id": 118489044882, "name": "integrate", "conclusion": "skipped",
             "failing_steps": [], "annotations": []},
        ],
    },
}


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get(url: str, timeout: float = 30.0):
    req = urllib.request.Request(url, headers={"User-Agent": "lex-evaluation-team"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def fetch_run(run_id: str) -> dict:
    """Live fetch; raises EnvironmentError-derived exception on any failure."""
    run = get(f"{API}/actions/runs/{run_id}")
    jobs_payload = get(f"{API}/actions/runs/{run_id}/jobs?per_page=50")
    jobs = []
    for job in jobs_payload.get("jobs", []):
        anns = []
        if job.get("conclusion") == "failure":
            try:
                raw = get(f"{API}/check-runs/{job['id']}/annotations")
                anns = [{"level": a.get("annotation_level"),
                         "message": a.get("message"),
                         "path": a.get("path"),
                         "start_line": a.get("start_line"),
                         "end_line": a.get("end_line")}
                        for a in raw]
            except Exception:
                anns = [{"level": "undetermined",
                         "message": "annotations endpoint unreachable"}]
        jobs.append({
            "id": job["id"],
            "name": job["name"],
            "conclusion": job.get("conclusion"),
            "failing_steps": [s["name"] for s in job.get("steps", [])
                              if s.get("conclusion") not in ("success", "skipped", None)],
            "annotations": anns,
        })
    return {
        "name": run.get("name"),
        "conclusion": run.get("conclusion"),
        "event": run.get("event"),
        "head_sha": run.get("head_sha"),
        "created_at": run.get("created_at"),
        "updated_at": run.get("updated_at"),
        "jobs": jobs,
    }


def log_endpoint_probe(run_id: str) -> dict:
    """Record that the job-log zip is unreachable unauthenticated (403)."""
    url = f"{API}/actions/runs/{run_id}/logs"
    try:
        get(url, timeout=20)
        return {"url": url, "http_status": "200 (unexpected)", "reachable": True}
    except urllib.error.HTTPError as exc:
        return {"url": url, "http_status": exc.code, "reachable": False,
                "note": ("the exact out-of-scope paths named by the scope guard live "
                         "only in the job logs, which require authentication; they are "
                         "recorded as UNDETERMINED, never invented")}
    except Exception as exc:  # pragma: no cover - defensive
        return {"url": url, "http_status": None, "reachable": False,
                "error": f"{type(exc).__name__}: {exc}"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject-run", default="39380758180")
    ap.add_argument("--producer-run", default="39379766198")
    ap.add_argument("--out", default=None)
    ap.add_argument("--offline", action="store_true",
                    help="use the pinned fallback values without calling the API")
    args = ap.parse_args(argv)

    live: dict[str, dict] = {}
    api_ok = not args.offline
    for run_id in (args.subject_run, args.producer_run):
        if api_ok:
            try:
                live[run_id] = fetch_run(run_id)
                live[run_id]["_source"] = "live_github_rest_api"
            except Exception as exc:
                api_ok = False
                live[run_id] = json.loads(json.dumps(PINNED[run_id]))
                live[run_id]["_source"] = "pinned_fallback"
                live[run_id]["_fallback_reason"] = f"{type(exc).__name__}: {exc}"
        else:
            live[run_id] = json.loads(json.dumps(PINNED[run_id]))
            live[run_id]["_source"] = "pinned_fallback"
            live[run_id]["_fallback_reason"] = "args.offline"

    subject = live[args.subject_run]
    producer = live[args.producer_run]

    def job(run: dict, name: str) -> dict | None:
        for j in run.get("jobs", []):
            if j["name"] == name:
                return j
        return None

    subj_team = job(subject, "team") or {}
    prod_audit = job(producer, "audit") or {}
    prod_team = job(producer, "team") or {}

    record = {
        "schema": "lex-evaluation-orchestration-failure-diagnosis/1",
        "run_id": RUN_ID,
        "direction_version": 60,
        "generated_at_utc": utcnow(),
        "dispatch_mode": "OPERATIONAL_RESUME from the persisted producer snapshot "
                        f"{SNAPSHOT_BASE} (runs {args.subject_run} then "
                        f"{args.producer_run} left no durable delta)",
        "evidence_source": ("GitHub REST API (public repo) at execution time"
                            if any(v.get("_source") == "live_github_rest_api"
                                   for v in live.values())
                            else "pinned fallback captured 2026-10-20T06:5xZ"),
        "log_endpoint_access": {
            run_id: log_endpoint_probe(run_id) for run_id in live
        },
        "runs": live,
        "diagnosis": "TWO_STAGED_FAILURES_ONE_DELTA_ONE_SCOPE_GUARD",
        "summary": (
            f"Run {args.producer_run} (producer) produced real evaluation work - the "
            "team job succeeded and committed the snapshot "
            f"{SNAPSHOT_BASE} containing the packet-of-record stand-ready discharge "
            "(results/evaluation/packet_of_record_stand_ready/"
            f"{args.producer_run}.json, battery DISCHARGED) - but its AUDIT job "
            "aborted at the scope guard with exit 3 and the single-line annotation "
            "'auditor crossed scope:'. Because 'Persist audit snapshot' and "
            "'integrate' were skipped, no /audit ref and no gate file exist for that "
            "run, so nothing it produced could be audited or promoted. "
            f"Run {args.subject_run} (the first resume of that snapshot) then failed "
            "for an independent reason: the team step exited 67 "
            "LEX_ZERO_DELTA_REPAIR because the snapshot already WAS the HEAD and the "
            "working tree was clean - a zero-delta repair, exactly the rc the "
            "wrapper promises when a lane resumes without a new durable deliverable. "
            "Neither failure is a Product finding: no frozen bar was re-derived, no "
            "adjudication was weakened and no accepted artifact was edited."),
        "established_with_machine_evidence": [
            {"fact": f"run {args.subject_run} team step 'Run lane cycle' failed",
             "job_id": subj_team.get("id"),
             "conclusion": subj_team.get("conclusion"),
             "annotations": subj_team.get("annotations"),
             "source": subject.get("_source")},
            {"fact": "exit code 67 == LEX_ZERO_DELTA_REPAIR (wrapper contract on "
                     "main: LEX_REQUIRE_DELTA=1 for the evaluation lane)",
             "annotation_present": any(
                 "LEX_ZERO_DELTA_REPAIR" in (a.get("message") or "")
                 for a in (subj_team.get("annotations") or [])),
             "source": subject.get("_source")},
            {"fact": f"run {args.producer_run} team job succeeded (work existed)",
             "job_id": prod_team.get("id"),
             "conclusion": prod_team.get("conclusion"),
             "source": producer.get("_source")},
            {"fact": f"run {args.producer_run} audit job failed at the scope guard",
             "job_id": prod_audit.get("id"),
             "failing_steps": prod_audit.get("failing_steps"),
             "annotations": prod_audit.get("annotations"),
             "source": producer.get("_source")},
            {"fact": "audit + integrate were skipped on both runs, so no /audit ref "
                     "or gate file exists for either run and neither snapshot was "
                     "promoted by the integrate job",
             "jobs": [{"name": j["name"], "conclusion": j["conclusion"]}
                      for j in producer.get("jobs", [])]
                     + [{"name": j["name"], "conclusion": j["conclusion"]}
                        for j in subject.get("jobs", [])]},
        ],
        "undetermined_bounded": [
            {"item": "the exact out-of-scope paths the auditor wrote in "
                     f"{args.producer_run}",
             "why": "the scope-guard annotation truncates at 'auditor crossed "
                    "scope:' and the job-log zip endpoint answers HTTP 403 to an "
                    "unauthenticated client (recorded above under "
                    "log_endpoint_access); inventing the paths would be a "
                    "fabrication",
             "bounded_by": "the guard fired inside the audit job, so the crossed "
                           "path is OUTSIDE results/audit/evaluation and "
                           "state/evaluation.json (the auditor's two in-scope "
                           "targets); ranked by the prior defect classes below"},
            {"item": "whether the crossing was a write, a read outside the read "
                     "gate, or a staging side-effect",
             "why": "exit 3 is the guard's single failure code; the annotation "
                    "carries no write/read distinction"},
        ],
        "prior_defect_classes": [
            {"class": "ref-coverage artifact",
             "why_possible": "the auditor's fetch only stages lab/evaluation plus "
                             "the current run's team/audit refs, so any instrument "
                             "that opens another lab ref (e.g. "
                             "origin/lab/frontier/frontier-packet-serve-audit) "
                             "touches a path outside its checkout"},
            {"class": "outside-scope write (results/ or state/ of another lane)",
             "why_possible": "the lane scope guard is path-based and fires on the "
                             "first crossed path, so a single stray write aborts "
                             "the whole audit job"},
            {"class": "scratch/staging path outside the two in-scope directories",
             "why_possible": "a temp file created under the repo root instead of "
                             "$RUNNER_TEMP is still inside the audited tree"},
        ],
        "repairs_executed_by_this_run": [
            "Frozen-first cross-check hypothesis + freeze record committed BEFORE "
            "any claim-bearing execution "
            "(evaluation/SERVE_VERDICT_CROSSCHECK_HYPOTHESIS_V1.json, sha "
            "0c9b4bba7ece03378d4402752613b2a706d094e5147f0089ad7c1773956ca0a5).",
            "The ACCEPTED serve verdict was VENDORED with byte-exact provenance "
            "(sha256 403aeb0c..., git blob oid d7577401...) so the cross-check "
            "reproduces in a bare checkout without touching any lab ref - the "
            "ref-coverage defect class cannot recur for this instrument.",
            "results/evaluation/serve_verdict_crosscheck/39381093325.json: the "
            "side-by-side table direction v60 ordered (26 comparable quantities, "
            "ZERO_DIVERGENCE, 5 non-vacuity controls).",
            "This record, plus the twin pytest/shim readings and the cycle report, "
            "constitute the durable delta whose absence produced exit 67.",
        ],
        "is_not": [
            "NOT a Product finding: no frozen bar, rubric, threshold, incumbent or "
            "predicate was re-derived, edited or re-tuned.",
            "NOT a claim about label or geometry soundness; both stay ABSOLUTELY "
            "UNPROVEN and both frozen bars stay unmet.",
            "NOT a claim that the auditor misbehaved: the scope guard is working "
            "as designed and correctly refused to publish unaudited results.",
            "NOT a guess at the crossed paths - they are recorded as UNDETERMINED.",
            "NOT an override of the accepted BOUNDED-NEGATIVE serve verdict; both "
            "DO-NOT-SERVE orders stand.",
        ],
        "consequence_for_this_resume": [
            "This run must leave a non-empty durable delta (committed HEAD change) "
            "or it repeats exit 67; every artifact it publishes is under this run "
            "id and inside the evaluation write scope.",
            "The producer snapshot's discharge work is RE-USED, not rewritten: the "
            "cross-check re-hashes it and places it beside the team's independent "
            "recomputation.",
            "The state sentence 'No serve verdict has landed.' written by the "
            "producer run is superseded in place-by-addition (preserved verbatim "
            "beside its correction), never deleted.",
            "The independent audit of THIS run must keep every write inside "
            "results/audit/evaluation and every read inside the declared read "
            "gate; the vendored verdict exists precisely so no lab ref is needed.",
        ],
        "recovery_path": (
            f"the resilience job of {args.subject_run} dispatched this run "
            f"{RUN_ID} as resume_from_run_id={args.subject_run} (operational "
            "recovery, not audit repair); this run's own independent audit writes "
            f"results/audit/evaluation/CYCLE_{RUN_ID}_GATE.json and the integrate "
            "job promotes on gate=PASS."),
    }

    text = json.dumps(record, indent=1)
    print(text)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
