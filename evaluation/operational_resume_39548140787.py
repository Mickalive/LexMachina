#!/usr/bin/env python3
"""Operational-resume instrument for the evaluation lane, resumed run 39548140787.

WHY THIS INSTRUMENT EXISTS
--------------------------
Run 39548140787's producer snapshot survived, but its audit job died before any
independent gate was produced, and the snapshot itself cites claim-bearing
artifacts that are not in its own committed tree.  This instrument names the
orchestration/validation failure from machine-readable evidence, audits every
claim reference the snapshot publishes, cross-checks the snapshot's published
benchmark quantities against three already-committed artifacts AND against this
run's fresh re-execution, and - in its ``verify`` phase - proves the state
restoration and the repaired references.

It re-derives NOTHING.  No frozen bar, rubric, threshold, success rule,
population predicate or metric is read for anything except a re-hash.

Exit codes (frozen in OPERATIONAL_RESUME_39548140787_HYPOTHESIS_V1)
--------------------------------------------------------------------
0  RESUME_AUDIT_READY  - every expected finding held
1  RESUME_FINDING_FAIL - at least one expected finding failed / not measured
2  NOT_MEASURED        - environment error: frozen pin drift, missing cache,
                         missing frozen spec (never a pass)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SCHEMA = "lex-evaluation-operational-resume/1"
RUN_ID = "39552967253"
RESUMED_FROM = "39548140787"
RESUMED_HEAD = "8fe862e83ade65dcd136e3bcba370347e50e7e66"
ACCEPTED_BASE = "b486e0ccc3a2df1ab0b86d8517ec90d90cdc7c49"
LAST_ACCEPTED_RUN = "39546829058"
DIRECTION_VERSION = 61

SUBJECT_STATE = "state/evaluation.json"
SUBJECT_REPORT = "reports/evaluation/CYCLE_local_1792559615.md"
NEW_MACHINE_RECORD = f"results/evaluation/query_map_cached_bundle_benchmark/{RUN_ID}.json"
NEW_REPORT = f"reports/evaluation/QUERY_MAP_CACHED_BUNDLE_{RUN_ID}.md"
PRIOR_ARTIFACTS = [
    "results/evaluation/query_map_cached_bundle_benchmark/local_test.json",
    "results/evaluation/query_map_cached_bundle_benchmark/39462322100.json",
    "results/evaluation/query_map_cached_bundle_benchmark/39200567493.json",
]
FROZEN_PINS: dict[str, str] = {
    "evaluation/retrieval_gate/frozen_retrieval_benchmark.json":
        "187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72",
    "evaluation/frozen_bars/RULES_LABEL.json":
        "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608",
    "evaluation/frozen_bars/RULES_GEOMETRY.json":
        "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633",
    "evaluation/frozen_bars/VERDICT_CONTRACT.json":
        "b9cdb89438a8d16ee165fe2a5d73060524154d8e7ba8e0cab867e8ca17ff414c",
}
FAIL_CLOSED_FLAGS = ["human_gate_ready", "machine_gate_ready", "packet_admitted",
                     "ready_for_owner_session", "owner_decision_required"]

#: Keys that were removed by the subject snapshot and are restored to their
#: PRESENCE but legitimately carry this cycle's content. Every other removed key
#: must come back byte-identical to the accepted base. This list is the whole
#: disclosure of which values changed; nothing else may differ.
#:
#: COUNT DISCLOSURE. The frozen hypothesis hand-counted 71 removed keys. The
#: machine-computed set difference (b486e0cc state keys minus 8fe862e8 state
#: keys) is 73. The SET rule governs: every key of that set must be present
#: again. The frozen hypothesis is NOT edited; the slip is disclosed here and in
#: the cycle report and the state file.
UPDATED_KEYS = [
    "accepted_run_id", "accepted_run_promotion_status", "claim_ceiling",
    "continue_recommended_reason", "cycle_status", "evidence_ref_corrections",
    "evidence_refs", "evidence_refs_n", "github_run", "last_verified_run",
    "last_verified_timestamp", "next_recommendation", "proposed_run_id",
    "pytest_execution_disclosure", "summary",
]
CLAIM_CEILING = (
    "This cycle may claim exactly: (a) which job and which step of run "
    "39548140787 failed, from the public run/job JSON, plus the resulting "
    "absence of an audit branch and of any promotion to lab/evaluation; (b) "
    "that the snapshot cited three claim-bearing artifacts absent from its own "
    "committed tree; (c) that the snapshot's published per-question "
    "measurements reproduce from three committed artifacts and from a fresh "
    "re-execution under run 39552967253; (d) that all 73 state keys the "
    "snapshot deleted (the frozen hypothesis hand-counted 71; the machine-"
    "computed set difference governs) are present again - 62 of them "
    "byte-identical to the accepted base, 11 carrying only the disclosed "
    "UPDATED_KEYS content - including the "
    "five fail-closed probes, and that the evidence references now resolve. It must NOT claim: the "
    "underlying CAUSE of the audit step failure (inference only - the job-log "
    "endpoint is inaccessible); any verdict, gate or admission on any packet; "
    "that the absolute LABEL_SOUND or GEOMETRY_SOUND bars are met; that either "
    "DO-NOT-SERVE order is lifted; that the map helps a jurist; that any "
    "Frontier component was rebuilt or re-scored; that run 39548140787 or run "
    "39552967253 is accepted (acceptance requires an independent gate=PASS plus "
    "an accept commit on lab/evaluation); or any unblocking of the human gate. "
    "human_gate_ready=false, machine_gate_ready=false, packet_admitted=false, "
    "ready_for_owner_session=false, owner_decision_required=false."
)

API_RUN = ("https://api.github.com/repos/Mickalive/LexMachina"
           f"/actions/runs/{RESUMED_FROM}")
API_JOBS = API_RUN + "/jobs?per_page=20"
API_LOG = ("https://api.github.com/repos/Mickalive/LexMachina"
           f"/actions/jobs/{{job_id}}/logs")


def _sha256(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=str(REPO_ROOT), check=True,
                          capture_output=True, text=True).stdout.strip()


def _git_bytes(*args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=str(REPO_ROOT), check=True,
                          capture_output=True).stdout


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _http_json(url: str, timeout: int = 30) -> tuple[int | None, Any]:
    req = urllib.request.Request(url, headers={
        "User-Agent": "lex-evaluation-operational-resume",
        "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:          # e.g. 403 on job logs
        return exc.code, {"error": str(exc)}
    except Exception as exc:                        # noqa: BLE001 - recorded, never raised
        return None, {"error": f"{type(exc).__name__}: {exc}"}


def fetch_prior_run_facts() -> dict[str, Any]:
    """Established facts from the public run/job JSON only.

    The step-level CAUSE is deliberately not asserted: the job-log endpoint is
    authenticated-only, so any statement about WHY the gate step failed is
    inference and is labelled as such in ``attribution``.
    """
    run_status, run_body = _http_json(API_RUN)
    job_status, job_body = _http_json(API_JOBS)
    log_status: int | None = None
    log_body: Any = None
    if job_status == 200 and isinstance(job_body, dict):
        audit = next((j for j in job_body.get("jobs", [])
                      if j.get("name") == "audit"), None)
        if audit and audit.get("id"):
            log_status, log_body = _http_json(API_LOG.format(job_id=audit["id"]))

    out: dict[str, Any] = {
        "source_run_api": API_RUN,
        "source_jobs_api": API_JOBS,
        "run_http_status": run_status,
        "jobs_http_status": job_status,
        "job_log_endpoint_http_status": log_status,
        "job_log_endpoint_body": log_body,
        "job_log_endpoint_accessible": log_status == 200,
        "job_log_note": ("job logs require repo admin; HTTP 401/403 means the "
                         "step-level CAUSE cannot be established from this "
                         "workspace and every such attribution is INFERENCE"),
    }
    if run_status == 200 and isinstance(run_body, dict):
        out["run"] = {
            "id": run_body.get("id"),
            "name": run_body.get("name"),
            "status": run_body.get("status"),
            "conclusion": run_body.get("conclusion"),
            "head_branch": run_body.get("head_branch"),
            "head_sha": run_body.get("head_sha"),
            "created_at": run_body.get("created_at"),
            "updated_at": run_body.get("updated_at"),
            "event": run_body.get("event"),
        }
    if job_status == 200 and isinstance(job_body, dict):
        jobs = []
        for j in job_body.get("jobs", []):
            steps = [{"number": s.get("number"), "name": s.get("name"),
                      "conclusion": s.get("conclusion")} for s in j.get("steps", [])]
            failed = [s for s in steps if s["conclusion"] == "failure"]
            jobs.append({"name": j.get("name"), "status": j.get("status"),
                         "conclusion": j.get("conclusion"),
                         "n_steps": len(steps),
                         "failed_steps": failed,
                         "skipped_steps": [s for s in steps
                                           if s["conclusion"] == "skipped"],
                         "steps": steps})
        out["jobs"] = jobs
    else:
        out["jobs"] = None
    return out


def git_branch_facts() -> dict[str, Any]:
    def lsremote(pattern: str) -> dict[str, str]:
        try:
            raw = _git("ls-remote", "origin", pattern)
        except subprocess.CalledProcessError as exc:
            return {"error": f"ls-remote failed: {exc.stderr.strip()[:200]}"}
        refs = {}
        for line in raw.splitlines():
            if "\t" in line:
                sha, ref = line.split("\t", 1)
                refs[ref] = sha
        return refs

    team = lsremote(f"refs/heads/cycle/core/evaluation/{RESUMED_FROM}/*")
    lab = lsremote("refs/heads/lab/evaluation")
    return {
        "resumed_snapshot_refs": team,
        "audit_branch_exists": any("audit" in r for r in team),
        "team_branch_exists": any(r.endswith("/team") for r in team),
        "lab_evaluation_refs": lab,
        "lab_evaluation_head": lab.get("refs/heads/lab/evaluation"),
        "lab_evaluation_advanced_past_accepted_base":
            lab.get("refs/heads/lab/evaluation") not in (None, ACCEPTED_BASE),
        "accepted_base_expected": ACCEPTED_BASE,
        "worktree_head": _git("rev-parse", "HEAD"),
        "worktree_branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
    }


def _committed_paths(rev: str) -> set[str]:
    return set(_git("ls-tree", "-r", "--name-only", rev).splitlines())


def audit_subject_references() -> dict[str, Any]:
    """Every claim-bearing path the SUBJECT snapshot publishes, and whether it
    exists in the SUBJECT commit (the question that decides audit-readiness)."""
    subject_paths = _committed_paths(RESUMED_HEAD)
    subject_state = json.loads(_git_bytes("show", f"{RESUMED_HEAD}:{SUBJECT_STATE}"))

    refs: list[str] = list(subject_state.get("evidence_refs") or [])
    bench = subject_state.get("benchmark_result") or {}
    if bench.get("run_id"):
        refs.append(f"query_map_cached_bundle_benchmark run_id={bench['run_id']}")

    state_missing = [r for r in (subject_state.get("evidence_refs") or [])
                     if not r.startswith("/") and not (REPO_ROOT / r).exists()
                     and r not in subject_paths]

    report_text = _git_bytes("show", f"{RESUMED_HEAD}:{SUBJECT_REPORT}").decode("utf-8")
    cited = []
    for token in report_text.replace("`", "\n").splitlines():
        token = token.strip()
        if (token.startswith("results/") or token.startswith("reports/")) \
                and "*" not in token and " " not in token:
            cited.append(token)
    seen: set[str] = set()
    cited_unique = [c for c in cited if not (c in seen or seen.add(c))]
    report_missing = [c for c in cited_unique if c not in subject_paths]

    bench_run = (subject_state.get("benchmark_result") or {}).get("run_id")
    bundle_prefix = (f"results/evaluation/query_map_cached_bundle_benchmark/"
                     f"bundles/{bench_run}_")
    bundle_matches = sorted(p for p in subject_paths if p.startswith(bundle_prefix))

    claimed_machine = (f"results/evaluation/query_map_cached_bundle_benchmark/"
                       f"{bench_run}.json")
    claimed_report = (f"reports/evaluation/QUERY_MAP_CACHED_BUNDLE_{bench_run}.md")
    claimed_bundle_glob = f"{bundle_prefix}*.json"

    return {
        "subject_commit": RESUMED_HEAD,
        "subject_state_evidence_refs": subject_state.get("evidence_refs"),
        "subject_state_evidence_refs_missing_from_subject_commit": state_missing,
        "subject_state_evidence_refs_present":
            [r for r in (subject_state.get("evidence_refs") or [])
             if r not in state_missing],
        "n_evidence_refs": len(subject_state.get("evidence_refs") or []),
        "n_evidence_refs_missing": len(state_missing),
        "subject_report": SUBJECT_REPORT,
        "subject_report_sha256": hashlib.sha256(
            _git_bytes("show", f"{RESUMED_HEAD}:{SUBJECT_REPORT}")).hexdigest(),
        "report_cited_paths": cited_unique,
        "report_cited_paths_missing_from_subject_commit": report_missing,
        "subject_report_claimed_run_id": bench_run,
        "claimed_artifacts": {
            claimed_machine: claimed_machine in subject_paths,
            claimed_report: claimed_report in subject_paths,
            claimed_bundle_glob: bool(bundle_matches),
        },
        "claimed_bundle_glob_prefix": bundle_prefix,
        "claimed_bundle_glob_matches_in_subject_commit": bundle_matches,
        "n_claimed_artifacts_absent": sum(
            1 for v in (claimed_machine in subject_paths,
                        claimed_report in subject_paths,
                        bool(bundle_matches)) if not v),
        "subject_state_top_level_keys": sorted(subject_state),
        "n_subject_state_keys": len(subject_state),
        "refs": refs,
    }


def audit_state_key_delta() -> dict[str, Any]:
    base = json.loads(_git_bytes("show", f"{ACCEPTED_BASE}:{SUBJECT_STATE}"))
    subj = json.loads(_git_bytes("show", f"{RESUMED_HEAD}:{SUBJECT_STATE}"))
    removed = sorted(set(base) - set(subj))
    return {
        "accepted_base_commit": ACCEPTED_BASE,
        "subject_commit": RESUMED_HEAD,
        "n_keys_accepted_base": len(base),
        "n_keys_subject": len(subj),
        "removed_keys": removed,
        "n_removed_keys": len(removed),
        "fail_closed_flags_removed": [f for f in FAIL_CLOSED_FLAGS if f in removed],
        "fail_closed_flags_still_present_in_subject":
            [f for f in FAIL_CLOSED_FLAGS if f in subj],
        "byte_sha256_accepted_base": hashlib.sha256(
            _git_bytes("show", f"{ACCEPTED_BASE}:{SUBJECT_STATE}")).hexdigest(),
        "byte_sha256_subject": hashlib.sha256(
            _git_bytes("show", f"{RESUMED_HEAD}:{SUBJECT_STATE}")).hexdigest(),
    }


def _vector_from_artifact(rec: dict) -> dict[str, dict]:
    out = {}
    for q in rec.get("questions", []):
        m = q.get("producer_meta", {})
        r = q.get("recall_measured_not_thresholded", {})
        kr, kc = r.get("known_relevant", {}), r.get("known_counter_reach", {})
        out[q["slug"]] = {
            "decisions": m.get("n_decisions"),
            "clusters": m.get("n_clusters"),
            "counter_candidates": m.get("n_counter_candidates"),
            "duplicates_suppressed": m.get("n_duplicates_suppressed"),
            "leg1_pass": bool(q["leg1_producer_baseline"]["pass"]),
            "leg2_fired": bool(q["leg2_falsification_blanked_counter_evidence"]["fired"]),
            "leg3_fired": bool(q["leg3_falsification_broken_source_url"]["fired"]),
            "known_relevant": f"{kr.get('found')}/{kr.get('expected')}",
            "known_counter_reach": f"{kc.get('found')}/{kc.get('expected')}",
        }
    return out


def _vector_from_state(bench: dict) -> dict[str, dict]:
    out = {}
    for q in bench.get("questions", []):
        out[q["slug"]] = {
            "decisions": q.get("decisions"),
            "clusters": q.get("clusters"),
            "counter_candidates": q.get("counter_candidates"),
            "duplicates_suppressed": q.get("duplicates_suppressed"),
            "leg1_pass": q.get("leg1_pass"),
            "leg2_fired": q.get("leg2_fired"),
            "leg3_fired": q.get("leg3_fired"),
            "known_relevant": str(q.get("known_relevant_recall", "")).split(" ")[0],
            "known_counter_reach": str(q.get("known_counter_reach", "")).split(" ")[0],
        }
    return out


def cross_check_benchmark() -> dict[str, Any]:
    subject_state = json.loads(_git_bytes("show", f"{RESUMED_HEAD}:{SUBJECT_STATE}"))
    subj_vec = _vector_from_state(subject_state.get("benchmark_result") or {})

    sources: dict[str, Any] = {}
    for rel in PRIOR_ARTIFACTS:
        p = REPO_ROOT / rel
        sources[rel] = {
            "exists": p.is_file(),
            "sha256": _sha256(p),
            "vector": _vector_from_artifact(json.loads(p.read_text())) if p.is_file() else None,
            "top_level": {k: json.loads(p.read_text()).get(k)
                          for k in ("run_id", "verdict", "exit_code",
                                    "falsification_proven", "n_questions")}
            if p.is_file() else None,
        }
    new_p = REPO_ROOT / NEW_MACHINE_RECORD
    new_rec = json.loads(new_p.read_text()) if new_p.is_file() else {}
    sources[NEW_MACHINE_RECORD] = {
        "exists": new_p.is_file(),
        "sha256": _sha256(new_p),
        "vector": _vector_from_artifact(new_rec) if new_p.is_file() else None,
        "top_level": {k: new_rec.get(k) for k in ("run_id", "verdict", "exit_code",
                                                  "falsification_proven",
                                                  "n_questions")}
        if new_p.is_file() else None,
        "frozen_spec": new_rec.get("frozen_spec"),
        "cache": new_rec.get("cache"),
        "counter_authority_yield": new_rec.get("counter_authority_yield"),
    }

    per_source_match = {}
    for rel, payload in sources.items():
        per_source_match[rel] = {
            "vector_present": payload["vector"] is not None,
            "matches_subject_state_vector": payload["vector"] == subj_vec
            if payload["vector"] is not None else False,
            "slugs": sorted(payload["vector"]) if payload["vector"] else None,
        }
    new_vec = sources[NEW_MACHINE_RECORD]["vector"]
    prior_pairs = {}
    for a in PRIOR_ARTIFACTS:
        for b in PRIOR_ARTIFACTS:
            if a < b and sources[a]["vector"] is not None and sources[b]["vector"] is not None:
                prior_pairs[f"{a} == {b}"] = sources[a]["vector"] == sources[b]["vector"]

    zero_yield_new = None
    if new_rec:
        zero_yield_new = new_rec.get("counter_authority_yield", {}).get(
            "questions_with_zero_counter_candidates")
    zero_yield_subject = (subject_state.get("benchmark_result") or {}).get(
        "counter_authority_yield_finding")

    return {
        "subject_state_run_id": (subject_state.get("benchmark_result") or {}).get("run_id"),
        "subject_state_vector": subj_vec,
        "sources": sources,
        "per_source_match": per_source_match,
        "all_sources_match_subject_state": all(
            v["matches_subject_state_vector"] for v in per_source_match.values()),
        "prior_pairwise_identity": prior_pairs,
        "new_matches_all_priors": all(
            per_source_match[rel]["matches_subject_state_vector"] for rel in PRIOR_ARTIFACTS
            if sources[rel]["vector"] is not None),
        "new_artifact_verdict": new_rec.get("verdict"),
        "new_artifact_exit_code": new_rec.get("exit_code"),
        "new_artifact_falsification_proven": new_rec.get("falsification_proven"),
        "new_zero_yield_questions": zero_yield_new,
        "subject_state_counter_authority_finding": zero_yield_subject,
        "frozen_spec_sha256_before": (new_rec.get("frozen_spec") or {}).get("sha256_before"),
        "frozen_spec_sha256_after": (new_rec.get("frozen_spec") or {}).get("sha256_after"),
    }


def rehash_frozen_pins() -> dict[str, Any]:
    got = {rel: _sha256(REPO_ROOT / rel) for rel in FROZEN_PINS}
    return {"expected": FROZEN_PINS, "observed": got,
            "all_match": all(got[k] == v for k, v in FROZEN_PINS.items())}


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=1, ensure_ascii=False,
                               sort_keys=True) + "\n", encoding="utf-8")


def phase_diagnosis(out_dir: Path) -> int:
    api = fetch_prior_run_facts()
    branches = git_branch_facts()
    refs = audit_subject_references()
    keys = audit_state_key_delta()
    cross = cross_check_benchmark()
    pins = rehash_frozen_pins()

    jobs = api.get("jobs") or []
    by_name = {j["name"]: j for j in jobs}
    audit_job = by_name.get("audit")
    f2_holds = bool(
        api.get("run", {}).get("conclusion") == "failure"
        and by_name.get("team", {}).get("conclusion") == "success"
        and audit_job and audit_job.get("conclusion") == "failure"
        and any(s["name"] == "Enforce audit scope and read gate"
                for s in audit_job.get("failed_steps", []))
        and any(s["name"] == "Independent audit"
                and s["conclusion"] == "success" for s in audit_job.get("steps", []))
        and any(s["name"] == "Persist audit snapshot"
                and s["conclusion"] == "skipped" for s in audit_job.get("steps", []))
        and by_name.get("integrate", {}).get("conclusion") == "skipped")

    findings = {
        "F1_no_audit_branch": {
            "holds": (branches.get("audit_branch_exists") is False
                      and branches.get("team_branch_exists") is True
                      and branches.get("lab_evaluation_head") == ACCEPTED_BASE),
            "observed": {k: branches.get(k) for k in (
                "audit_branch_exists", "team_branch_exists",
                "lab_evaluation_head", "lab_evaluation_advanced_past_accepted_base")},
        },
        "F2_failed_step": {
            "holds": f2_holds,
            "measured": api.get("jobs") is not None and api.get("run") is not None,
            "attribution": ("INFERENCE, not established fact: which of the gate "
                            "step's two clauses (the out-of-scope write check, or "
                            "the jq read of results/audit/evaluation/"
                            f"CYCLE_{RESUMED_FROM}_GATE.json) actually tripped "
                            "cannot be read - the job-log endpoint returned HTTP "
                            f"{api.get('job_log_endpoint_http_status')}"),
        },
        "F3_missing_refs": {
            "holds": (refs["n_evidence_refs_missing"] == 2
                      and refs["n_claimed_artifacts_absent"] == 3),
            "n_evidence_refs": refs["n_evidence_refs"],
            "n_evidence_refs_missing": refs["n_evidence_refs_missing"],
            "missing": refs["subject_state_evidence_refs_missing_from_subject_commit"],
            "n_claimed_artifacts_absent": refs["n_claimed_artifacts_absent"],
            "claimed_artifacts": refs["claimed_artifacts"],
        },
        "F4_content_reproduces": {
            "holds": bool(cross["all_sources_match_subject_state"]
                          and all(cross["prior_pairwise_identity"].values())
                          and cross["new_matches_all_priors"]),
            "per_source_match": cross["per_source_match"],
            "prior_pairwise_identity": cross["prior_pairwise_identity"],
        },
        "F5_reexecution": {
            "holds": bool(cross["new_artifact_verdict"] == "BENCHMARK_VALID_NO_FALSIFICATION"
                          and cross["new_artifact_exit_code"] == 0
                          and cross["new_artifact_falsification_proven"] is True
                          and cross["new_matches_all_priors"]
                          and set(cross["new_zero_yield_questions"] or []) == {
                              "corporate-criminal-liability",
                              "business-judgment-rule"}),
            "observed": {k: cross[k] for k in (
                "new_artifact_verdict", "new_artifact_exit_code",
                "new_artifact_falsification_proven", "new_matches_all_priors",
                "new_zero_yield_questions")},
        },
        "F6_state_restoration": {
            "holds": None,
            "phase": "diagnosis - verified by the verify phase after restoration",
            "n_removed_keys_pending_restore": keys["n_removed_keys"],
            "fail_closed_flags_removed": keys["fail_closed_flags_removed"],
        },
        "F7_pins": {"holds": pins["all_match"], "observed": pins["observed"]},
        "F8_pytest": {"holds": None, "phase": "measured separately"},
    }

    record = {
        "schema": SCHEMA,
        "record_kind": "diagnosis",
        "run_id": RUN_ID,
        "direction_version": DIRECTION_VERSION,
        "generated_at_utc": _now(),
        "resumed_from_run": RESUMED_FROM,
        "instrument": "evaluation/operational_resume_39548140787.py",
        "instrument_sha256": _sha256(Path(__file__)),
        "hypothesis_sha256": _sha256(REPO_ROOT / "evaluation" /
                                     "OPERATIONAL_RESUME_39548140787_HYPOTHESIS_V1.json"),
        "freeze_record_sha256": _sha256(REPO_ROOT / "evaluation" /
                                        "OPERATIONAL_RESUME_39548140787_FREEZE_RECORD_V1.json"),
        "prior_run_api": api,
        "branch_facts": branches,
        "subject_reference_audit": refs,
        "state_key_audit": keys,
        "benchmark_cross_check": cross,
        "frozen_pins": pins,
        "findings": findings,
        "frozen_pins_match_expected": pins["all_match"],
        "owner_decision_required": False,
        "human_gate_ready": False,
        "machine_gate_ready": False,
        "packet_admitted": False,
        "ready_for_owner_session": False,
        "claim_ceiling": CLAIM_CEILING,
    }

    # F6/F8 are verified by later phases; the diagnosis phase alone decides 0/1/2
    if not pins["all_match"]:
        record["verdict"] = "NOT_MEASURED"
        record["exit_code"] = 2
        record["detail"] = "frozen pin drift detected after execution; never a pass"
    else:
        decisive = {k: v for k, v in findings.items()
                    if k in ("F1_no_audit_branch", "F2_failed_step",
                             "F3_missing_refs", "F4_content_reproduces",
                             "F5_reexecution", "F7_pins")}
        ok = all(bool(v["holds"]) for v in decisive.values())
        record["verdict"] = ("RESUME_DIAGNOSIS_COMPLETE_PENDING_VERIFY" if ok
                             else "RESUME_FINDING_FAIL")
        record["exit_code"] = 0 if ok else 1

    _write(out_dir / f"{RUN_ID}_diagnosis.json", record)
    print(json.dumps({"verdict": record["verdict"],
                      "exit_code": record["exit_code"],
                      "findings": {k: v["holds"] for k, v in findings.items()},
                      "missing_refs": refs["subject_state_evidence_refs_missing_from_subject_commit"],
                      "n_removed_state_keys": keys["n_removed_keys"],
                      "frozen_pins_match": pins["all_match"],
                      "new_artifact": {k: cross[k] for k in (
                          "new_artifact_verdict", "new_artifact_exit_code",
                          "new_matches_all_priors")}}, indent=1))
    return int(record["exit_code"])


def phase_verify(out_dir: Path) -> int:
    state_path = REPO_ROOT / SUBJECT_STATE
    cur = json.loads(state_path.read_text(encoding="utf-8"))
    base = json.loads(_git_bytes("show", f"{ACCEPTED_BASE}:{SUBJECT_STATE}"))
    removed = sorted(set(base) - set(json.loads(
        _git_bytes("show", f"{RESUMED_HEAD}:{SUBJECT_STATE}"))))

    restored = {k: (k in cur) for k in removed}
    removed_updated = [k for k in removed if k in UPDATED_KEYS]
    static_keys = [k for k in removed if k in cur and k not in UPDATED_KEYS]
    byte_exact = {k: hashlib.sha256(json.dumps(base[k], sort_keys=True,
                                               ensure_ascii=False,
                                               default=str).encode()).hexdigest()
                  == hashlib.sha256(json.dumps(cur[k], sort_keys=True,
                                               ensure_ascii=False,
                                               default=str).encode()).hexdigest()
                  for k in static_keys}
    updated_present = {k: (k in cur) for k in UPDATED_KEYS}
    updated_changed = {k: json.dumps(base.get(k), sort_keys=True, ensure_ascii=False,
                                     default=str)
                       != json.dumps(cur.get(k), sort_keys=True, ensure_ascii=False,
                                     default=str)
                       for k in UPDATED_KEYS}

    live_refs = list(cur.get("evidence_refs") or [])
    ref_status = {r: (REPO_ROOT / r).exists() for r in live_refs}

    flags = {f: cur.get(f, "ABSENT") for f in FAIL_CLOSED_FLAGS}
    pins = rehash_frozen_pins()

    new_record_exists = (REPO_ROOT / NEW_MACHINE_RECORD).is_file()
    new_report_exists = (REPO_ROOT / NEW_REPORT).is_file()
    bench = cur.get("benchmark_result") or {}

    # Recompute the SUBJECT snapshot's reference defects is_file-aware, using
    # the lane's own rule (test_audit_correction_verification.py::
    # test_evidence_refs_exist asserts Path(ref).is_file()).
    subj_state = json.loads(_git_bytes("show", f"{RESUMED_HEAD}:{SUBJECT_STATE}"))
    subj_ref_status = {r: {"exists": (REPO_ROOT / r).exists(),
                           "is_file": (REPO_ROOT / r).is_file()}
                       for r in (subj_state.get("evidence_refs") or [])}
    subj_bad = [r for r, s in subj_ref_status.items() if not s["is_file"]]

    # Cycle-report path audit. The cycle report is written AFTER the first
    # verify reading, so this check is vacuously true while the report is
    # absent and becomes binding from the final reading onward. It never
    # converts a missing report into a failure - only a report that cites a
    # path which does not exist.
    report_path = REPO_ROOT / f"reports/evaluation/CYCLE_{RUN_ID}.md"
    if report_path.is_file():
        tokens: set[str] = set()
        for line in report_path.read_text(encoding="utf-8").replace(
                "`", "\n").splitlines():
            tok = line.strip()
            if tok.startswith(("results/", "reports/", "evaluation/", "tests/")) \
                    and " " not in tok and "*" not in tok \
                    and not tok.endswith(":"):
                tokens.add(tok)
        missing_report_paths = sorted(t for t in tokens
                                      if not (REPO_ROOT / t).exists())
        report_audit = {"present": True,
                        "path": f"reports/evaluation/CYCLE_{RUN_ID}.md",
                        "n_cited_paths": len(tokens),
                        "missing": missing_report_paths,
                        "all_resolve": not missing_report_paths}
    else:
        report_audit = {"present": False,
                        "path": f"reports/evaluation/CYCLE_{RUN_ID}.md",
                        "n_cited_paths": 0,
                        "missing": [],
                        "all_resolve": True}

    checks = {
        "all_removed_keys_present": all(restored.values()),
        "all_non_updated_removed_keys_byte_exact_vs_accepted_base":
            all(byte_exact.values())
            and len(byte_exact) == len(removed) - len(removed_updated),
        "all_updated_keys_present": all(updated_present.values()),
        "all_updated_keys_changed_from_accepted_base": all(updated_changed.values()),
        "fail_closed_flags_present_and_false": all(flags[f] is False
                                                  for f in FAIL_CLOSED_FLAGS),
        "all_live_evidence_refs_resolve": all(ref_status.values())
        and len(live_refs) > 0,
        "all_live_evidence_refs_are_files": all(
            (REPO_ROOT / r).is_file() for r in live_refs),
        "accepted_run_id_corrected": cur.get("accepted_run_id") == LAST_ACCEPTED_RUN,
        "proposed_run_id_set": cur.get("proposed_run_id") == RUN_ID,
        "benchmark_record_points_at_this_runs_committed_artifact":
            bench.get("run_id") == RUN_ID and new_record_exists and new_report_exists,
        "direction_version_pinned": cur.get("direction_version") == DIRECTION_VERSION,
        "frozen_pins_intact": pins["all_match"],
        "subject_defective_report_preserved_byte_identical":
            _sha256(REPO_ROOT / SUBJECT_REPORT) ==
            "93a0b580b309e83b0ab9c7488c679d66c133e836eb7626fab1e33eb19fcff6b3",
        "no_state_key_lost_vs_accepted_base": set(base) <= set(cur),
        "cycle_report_references_resolve_if_written": report_audit["all_resolve"],
    }

    payload = {
        "schema": SCHEMA,
        "record_kind": "verify",
        "run_id": RUN_ID,
        "direction_version": DIRECTION_VERSION,
        "generated_at_utc": _now(),
        "resumed_from_run": RESUMED_FROM,
        "instrument": "evaluation/operational_resume_39548140787.py",
        "accepted_base_commit": ACCEPTED_BASE,
        "subject_commit": RESUMED_HEAD,
        "n_removed_keys": len(removed),
        "n_removed_keys_per_hypothesis_handcount": 71,
        "count_disclosure": ("the frozen hypothesis hand-counted 71 removed keys; "
                             "the machine-computed set difference "
                             "(b486e0cc state keys minus 8fe862e8 state keys) is 73. "
                             "The set rule governs and the hypothesis is not edited."),
        "updated_keys": UPDATED_KEYS,
        "removed_keys_that_are_updated": removed_updated,
        "n_removed_keys_that_are_updated": len(removed_updated),
        "n_removed_non_updated_keys": len(removed) - len(removed_updated),
        "restored": restored,
        "n_restored": sum(1 for v in restored.values() if v),
        "restored_byte_exact_non_updated": byte_exact,
        "n_restored_byte_exact_non_updated": sum(1 for v in byte_exact.values() if v),
        "updated_keys_present": updated_present,
        "updated_keys_changed_from_base": updated_changed,
        "fail_closed_flags": flags,
        "evidence_refs": ref_status,
        "subject_reference_defects_recomputed": {
            "subject_commit": RESUMED_HEAD,
            "rule": "tests/evaluation/test_audit_correction_verification.py::"
                    "test_evidence_refs_exist asserts Path(ref).is_file()",
            "status": subj_ref_status,
            "refs_failing_is_file": subj_bad,
            "n_refs": len(subj_ref_status),
            "n_failing_is_file": len(subj_bad),
            "n_missing_entirely": sum(1 for s in subj_ref_status.values()
                                      if not s["exists"]),
        },
        "new_machine_record": {"path": NEW_MACHINE_RECORD,
                               "sha256": _sha256(REPO_ROOT / NEW_MACHINE_RECORD)},
        "new_report": {"path": NEW_REPORT,
                       "sha256": _sha256(REPO_ROOT / NEW_REPORT)},
        "cycle_report_path_audit": report_audit,
        "checks": checks,
        "all_checks_hold": all(checks.values()),
        "verdict": "RESUME_AUDIT_READY" if all(checks.values()) else "RESUME_FINDING_FAIL",
        "exit_code": 0 if all(checks.values()) else 1,
        "frozen_pins": pins,
        "owner_decision_required": False,
        "human_gate_ready": False,
        "machine_gate_ready": False,
        "packet_admitted": False,
        "ready_for_owner_session": False,
        "claim_ceiling": CLAIM_CEILING,
    }
    _write(out_dir / f"{RUN_ID}_state_restoration_verify.json", payload)
    print(json.dumps({"verdict": payload["verdict"],
                      "exit_code": payload["exit_code"],
                      "n_removed": len(removed),
                      "n_restored": payload["n_restored"],
                      "n_restored_byte_exact_non_updated":
                          payload["n_restored_byte_exact_non_updated"],
                      "checks": checks}, indent=1))
    return int(payload["exit_code"])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--phase", choices=["diagnosis", "verify"], required=True)
    ap.add_argument("--out-dir",
                    default=str(REPO_ROOT / "results" / "evaluation" /
                                f"orchestration_resume_{RESUMED_FROM}"))
    args = ap.parse_args(argv)
    out_dir = Path(args.out_dir)
    if args.phase == "diagnosis":
        return phase_diagnosis(out_dir)
    return phase_verify(out_dir)


if __name__ == "__main__":
    raise SystemExit(main())
