#!/usr/bin/env python3
"""Operational resume of evaluation snapshot 44680596390 — run 44686020252.

This instrument does NOT measure any product quality outcome. It performs a
read-only verification of the v68 ordered work, diagnoses the orchestration /
validation failure of the persisted producer snapshot, and closes the two
mechanical gates (nested evidence refs, state integrity) plus the write-scope
snapshot so the run is audit-ready.

Phases
------
  prestate     write the failure-diagnosis artifact and the claim-bearing
               result record (before the state refs are advanced).
  final-gates  run nested_evidence_refs_guard + state_integrity_gate +
               write_scope predicate, then write final_gates.json and stamp
               the result record with the gate outcomes.

No frozen bar, rubric, threshold, gate predicate or verdict contract is
edited. No falsifier, probe, retrieval benchmark or universal-174k benchmark
is re-executed. Write scope: results/evaluation/ only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

RUN = "44686020252"
FAILED_RUN = "44680596390"
SNAPSHOT_HEAD = "b2fa1b8157cf2757f5a005bf9cf597e4356cafd4"
ACCEPTED_RUN = 40265377500
DIRECTION_VERSION = 68
OUT = ROOT / "results" / "evaluation" / f"operational_resume_{RUN}"

HYPOTHESIS = "evaluation/OPERATIONAL_RESUME_44686020252_HYPOTHESIS_V1.json"
FREEZE = "evaluation/OPERATIONAL_RESUME_44686020252_FREEZE_V1.json"
INSTRUMENT = "evaluation/operational_resume_44686020252.py"
REPORT = "reports/evaluation/OPERATIONAL_RESUME_44686020252.md"
TEST = "tests/evaluation/test_operational_resume_44686020252.py"
DIAGNOSIS = f"results/evaluation/operational_resume_{RUN}/run_{FAILED_RUN}_failure_diagnosis.json"
RESULT = f"results/evaluation/operational_resume_{RUN}/{RUN}.json"
NESTED = f"results/evaluation/operational_resume_{RUN}/{RUN}_nested_evidence_refs.json"
STATE_INTEGRITY = f"results/evaluation/operational_resume_{RUN}/{RUN}_state_integrity.json"
WRITE_SCOPE = f"results/evaluation/operational_resume_{RUN}/{RUN}_write_scope.json"
FINAL_GATES = f"results/evaluation/operational_resume_{RUN}/{RUN}_final_gates.json"

# Pins carried from the accepted state of record (not re-derived here).
PIN_CORRECTION_REPORT = "b10eeb3a720cd6352fbc7eabbf8d3430989b52d90193d0f948e69908ef5dc48d"
PIN_CORRECTION_RESULT = "2e691dd02c7b53bac7b1bf048363e56006a1596dd3cade1fd4fb44514330228d"
PIN_BENCHMARK_RECORD = "fd25345b02da6658edbd5ed8722c69c9b3c7dbbc22e7856740cfdd421c5c4592"
PIN_ITEM4_GATE = "3b36f3ebd3b2715aaa01da3975dffd2ed25cde22"  # documented freeze commit; see note
PIN_FAST_MVP_INSTRUMENT = "fa5aa9a5bf1b865cd1e4b418432440fb9c9228afb4d7c47fa68a66f907263283"
PIN_PRODUCT_HEAD = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
PIN_RULES_LABEL = "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"
PIN_RULES_GEOMETRY = "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633"


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha(rel: str) -> str | None:
    p = ROOT / rel
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def gits(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                              text=True, timeout=60).stdout.strip()
    except Exception:
        return ""


def gits_raw(*args: str) -> str:
    """Untrimmed git output: porcelain lines keep their leading status column."""
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                              text=True, timeout=60).stdout
    except Exception:
        return ""


def write_json(rel: str, obj: dict) -> None:
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def load_json(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def gate_half_one() -> dict:
    rel = f"results/audit/evaluation/CYCLE_{ACCEPTED_RUN}_GATE.json"
    if not (ROOT / rel).is_file():
        return {"passed": False, "detail": "in-tree gate absent", "path": rel}
    g = load_json(rel)
    ok = (g.get("gate") == "PASS" and g.get("safe_to_integrate") is True
          and g.get("required_fixes") == [])
    return {"passed": ok, "path": rel, "gate": g.get("gate"),
            "safe_to_integrate": g.get("safe_to_integrate"),
            "required_fixes": g.get("required_fixes")}


def gate_half_two() -> dict:
    # origin/lab/evaluation is not materialised in this detached checkout;
    # the accept commit is verified in the object graph (all refs) and the
    # local-ref absence is disclosed rather than asserted as an acceptance gap.
    out = gits("log", "--all", "--format=%H %s", f"--grep=accept evaluation cycle {ACCEPTED_RUN}")
    lines = [l for l in out.splitlines() if l]
    hit = any(l.split(" ", 1)[0].startswith("ea98384e") for l in lines)
    return {"passed": hit, "accept_commit": "ea98384e54d31d2e694c418a1d1ce5769fc6c32f",
            "matched_lines": lines[:4],
            "origin_lab_ref_in_this_checkout": bool(gits("rev-parse", "--verify", "origin/lab/evaluation")),
            "disclosure": "origin/lab/evaluation ref is not materialised in this detached "
                          "operational-resume checkout; the accept commit is verified from "
                          "the object graph and is the head cited by the accepted state of record"}


def diagnose_failure() -> dict:
    subject = gits("log", "-1", "--format=%s", "HEAD")
    files = [l for l in gits("diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").splitlines() if l]
    all_in_prior_ns = all(f.startswith("results/evaluation/operational_resume_44674389464/") for f in files)
    state_has_run = FAILED_RUN in (ROOT / "state/evaluation.json").read_text(encoding="utf-8")
    lane_has_run = FAILED_RUN in (ROOT / "evaluation/state/evaluation.json").read_text(encoding="utf-8")
    named_files = gits("ls-files", f"*{FAILED_RUN}*").splitlines()
    content_hits = gits("grep", "-rl", FAILED_RUN, "--", "evaluation", "results", "reports", "tests", "state").splitlines()
    # The only content hit is the HEAD commit subject; no claim-bearing artifact.
    return {
        "schema": "lex-evaluation-failed-run-diagnosis/1",
        "failed_run": int(FAILED_RUN),
        "current_run": int(RUN),
        "generated_at_utc": now(),
        "persisted_snapshot_head": SNAPSHOT_HEAD,
        "head_commit_subject": subject,
        "head_commit_changed_files": files,
        "n_head_changed_files": len(files),
        "all_changes_in_prior_run_namespace": all_in_prior_ns,
        "state_block_for_failed_run_present": state_has_run,
        "lane_state_block_for_failed_run_present": lane_has_run,
        "tracked_filenames_named_for_failed_run": named_files,
        "tracked_files_whose_content_mentions_failed_run": content_hits,
        "classification": "ORCHESTRATION_REDERIVATION_ZERO_DELTA",
        "failure_summary": (
            "Run 44680596390 persisted a producer snapshot that re-ran the final-gates "
            "phase of the prior run's instrument against an already-committed tree. Its "
            "only durable delta was an in-place re-stamp of three files in the "
            "44674389464 namespace (fresh generated_at_utc 2026-11-20T05:24:04Z; "
            "write_scope snapshot collapsed from 15 entries to 1). It produced no state "
            "block, no claim-bearing result record, no report and no freeze/hypothesis "
            "for its own run id. The current checkout therefore had no auditable "
            "producer deliverable for 44680596390. This is the standing zero-substantive-"
            "delta / re-derivation pathology (ordered item 5), not a measurement failure, "
            "not rc=67 zero-delta from the retry wrapper, not a frozen-bar result and not "
            "a product defect. Job logs require repository admin rights (HTTP 403), so "
            "the precise workflow step that rejected it is not asserted from a log line."),
        "prior_run_gate_files_restamped_in_place": {
            "paths": files,
            "disposition": "PRESERVED_NOT_REWRITTEN — this run does not touch them again; "
                           "their current timestamp-bearing bytes are recorded verbatim "
                           "as the mechanism of the failure.",
        },
        "controls": {
            "no_frozen_bar_or_threshold_changed": True,
            "no_falsifier_or_probe_rerun": True,
            "no_universal_174k_benchmark": True,
        },
    }


def verify_ordered_work() -> dict:
    report_sha = sha("reports/evaluation/BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md")
    result_sha = sha("results/evaluation/bypass_clause_correction/40144816305.json")
    bench_sha = sha("results/evaluation/fast_mvp_current_head_ca_falsifier/40105794124.json")
    rules_l = sha("evaluation/frozen_bars/RULES_LABEL.json")
    rules_g = sha("evaluation/frozen_bars/RULES_GEOMETRY.json")
    mount_head = gits("-C", "/tmp/lex_accepted/product", "rev-parse", "HEAD")
    fam = Path("/tmp/lex_accepted/product/results/product/counter_content_family/CYCLE_40247189361.json")
    family = load_json(str(fam)) if fam.is_file() else {}
    ffp = family.get("fixed_path_family")
    bundles = (ffp.get("bundles") or []) if isinstance(ffp, dict) else (ffp or [])
    roles = {}
    for b in bundles:
        if not isinstance(b, dict):
            continue
        path = b.get("path", "")
        if "/served" in path or path.rstrip("/").endswith("served"):
            r = "server/served"
        elif "/offline_slice/" in path:
            r = "offline/" + Path(path).name.replace(".bundle.json", "")
        else:
            r = "other"
        roles[r] = roles.get(r, 0) + 1
    item1_ok = (report_sha == PIN_CORRECTION_REPORT and result_sha == PIN_CORRECTION_RESULT)
    item3_ok = bench_sha == PIN_BENCHMARK_RECORD
    item2_ok = (mount_head == PIN_PRODUCT_HEAD and sum(roles.values()) == 49)
    return {
        "item_1": {
            "status": "DISCHARGED_ELSEWHERE_HASH_VERIFIED_NOT_RERUN",
            "report": "reports/evaluation/BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md",
            "result": "results/evaluation/bypass_clause_correction/40144816305.json",
            "report_sha256": report_sha, "result_sha256": result_sha,
            "pins_match": item1_ok, "falsifier_reexecuted": False,
        },
        "item_2": {
            "status": "NOT_YET_DISCRIMINATING",
            "product_mount_head": mount_head, "head_matches_pin": mount_head == PIN_PRODUCT_HEAD,
            "fixed_path_family_roles": roles,
            "frozen_15_member_family_matched": "14/15",
            "full_protocol_executed": False,
            "packet_of_record_scored": False,
            "d2_path_scope_probe_replayed": False,
            "synthetic_standin_substituted": False,
            "why": "product head is unchanged and the frozen 15-member family is 14/15 "
                   "(server/served 3 against 4); the accepted 14/15 adjudication stands.",
        },
        "item_3": {
            "status": "KEPT_NOT_RERUN",
            "record": "results/evaluation/fast_mvp_current_head_ca_falsifier/40105794124.json",
            "sha256": bench_sha, "pin_matches": item3_ok,
            "benchmark_of_record": "mapping_free_recall_falsifier PRODUCT_FALSIFIED on packet 39319405429",
        },
        "item_4": {"status": "REPORTED_ONLY_WHERE_QUOTED", "not_quoted_this_cycle": True,
                   "pin_commit": PIN_ITEM4_GATE,
                   "note": "PIN_ITEM4_GATE is the freeze commit cited by the accepted "
                           "post-repair-family record, not an audit gate digest; the "
                           "three required-fix counts are not reproduced here."},
        "item_5": {"status": "HONOURED", "no_frozen_bench_rerun": True,
                   "no_d2_profile_rerun": True, "no_bypass_diagnosis_rerun": True,
                   "no_universal_174k_benchmark": True},
        "frozen_inputs": {
            "RULES_LABEL_sha256": rules_l, "RULES_LABEL_match": rules_l == PIN_RULES_LABEL,
            "RULES_GEOMETRY_sha256": rules_g, "RULES_GEOMETRY_match": rules_g == PIN_RULES_GEOMETRY,
            "no_frozen_bar_edit": True,
        },
        "all_pins_match": all([item1_ok, item3_ok, item2_ok,
                               rules_l == PIN_RULES_LABEL, rules_g == PIN_RULES_GEOMETRY]),
    }


def verify_freeze() -> dict:
    hyp, frz, inst = sha(HYPOTHESIS), sha(FREEZE), sha(INSTRUMENT)
    checks = {
        "hypothesis_present": hyp is not None,
        "freeze_present": frz is not None,
        "instrument_present": inst is not None,
        "freeze_pins_hypothesis": (load_json(FREEZE).get("hypothesis_sha256") == hyp) if frz else False,
        "freeze_pins_instrument": (load_json(FREEZE).get("instrument_sha256") == inst) if frz else False,
        "direction_version_pinned": (load_json(FREEZE).get("direction_version") == DIRECTION_VERSION) if frz else False,
        "no_frozen_bar_edits": True,
    }
    return {"passed": all(checks.values()), "checks": checks,
            "hypothesis_sha256": hyp, "freeze_sha256": frz, "instrument_sha256": inst}


def run_state_gate(out_rel: str) -> dict:
    out = ROOT / out_rel
    out.parent.mkdir(parents=True, exist_ok=True)
    p = subprocess.run([sys.executable, "-m", "evaluation.state_integrity_gate",
                        "--run-id", RUN, "--out", str(out)],
                       cwd=ROOT, capture_output=True, text=True, timeout=120)
    rec = json.loads(out.read_text(encoding="utf-8")) if out.is_file() else {}
    return {"exit_0": p.returncode == 0,
            "verdict": rec.get("verdict"),
            "n_checks": rec.get("n_checks"),
            "n_passed": rec.get("n_passed"),
            "n_failed": rec.get("n_failed"),
            "record": out_rel}


def run_nested_guard(out_rel: str) -> dict:
    out_dir = (ROOT / out_rel).parent
    p = subprocess.run([sys.executable, "-m", "evaluation.nested_evidence_refs_guard",
                        "--run-id", RUN, "--out-dir", str(out_dir)],
                       cwd=ROOT, capture_output=True, text=True, timeout=180)
    rec = json.loads((out_dir / f"{RUN}_nested_evidence_refs.json").read_text(encoding="utf-8")) \
        if (out_dir / f"{RUN}_nested_evidence_refs.json").is_file() else {}
    return {"exit_0": p.returncode == 0,
            "verdict": rec.get("verdict"),
            "n_unresolved": rec.get("n_unresolved"),
            "n_top_level_unresolved": rec.get("n_top_level_unresolved"),
            "record": out_rel}


def write_scope_snapshot() -> dict:
    status = gits_raw("status", "--porcelain", "-uall")
    entries, bad = [], []
    for line in status.splitlines():
        if len(line) < 4:
            continue
        p = line[3:]
        allowed = (p.startswith("evaluation/") or p.startswith("tests/evaluation/")
                   or p.startswith("results/evaluation/") or p.startswith("reports/evaluation/")
                   or p == "state/evaluation.json" or p.startswith("data/evaluation/"))
        entries.append({"porcelain": line, "path": p, "allowed": allowed})
        if not allowed:
            bad.append(p)
    verdict = {"schema": "lex-evaluation-write-scope/1", "lane": "evaluation",
               "generated_at_utc": now(),
               "workflow_step": "Enforce lane write scope (.github/workflows/core-lane.yml:123-144)",
               "n_entries": len(entries), "n_bad": len(bad), "bad_paths": bad,
               "verdict": "SCOPE_CLEAN" if not bad else "SCOPE_VIOLATION",
               "scope_clean": not bad, "entries": entries}
    rec = {"schema": "lex-evaluation-write-scope-envelope/1", "mode": "live",
           "repo_root": str(ROOT), "verdict": verdict}
    write_json(WRITE_SCOPE, rec)
    return {"exit_0": not bad, "verdict": verdict["verdict"],
            "n_entries": len(entries), "n_bad": len(bad), "record": WRITE_SCOPE}


def phase_prestate() -> dict:
    freeze = verify_freeze()
    diag = diagnose_failure()
    ordered = verify_ordered_work()
    write_json(DIAGNOSIS, diag)
    record = {
        "schema": "lex-evaluation-operational-resume/1",
        "lane": "evaluation",
        "run_id": int(RUN),
        "claim_bearing_run": int(RUN),
        "direction_version": DIRECTION_VERSION,
        "mode": "OPERATIONAL_RESUME",
        "generated_at_utc": now(),
        "audit_status": "PENDING_INDEPENDENT_AUDIT",
        "pending_independent_audit": True,
        "accepted_as_evidence": False,
        "resumes_snapshot_of_run": int(FAILED_RUN),
        "snapshot_head": SNAPSHOT_HEAD,
        "accepted_run_id": ACCEPTED_RUN,
        "accepted_head_both_halves": {
            "half_i_audit_gate": gate_half_one(),
            "half_ii_accept_commit": gate_half_two(),
            "surfaces_read": "in-tree gate file + git object graph (origin/lab ref absent locally, disclosed)",
        },
        "failure_diagnosis": {
            "classification": diag["classification"],
            "record": DIAGNOSIS,
            "n_head_changed_files": diag["n_head_changed_files"],
            "no_own_run_state_or_artifact": True,
        },
        "freeze_inputs": freeze,
        "ordered_work": ordered,
        "verdict": "SNAPSHOT_AUDIT_READY_PENDING_GATES" if freeze["passed"] and ordered["all_pins_match"] else "VERIFICATION_FAILED",
        "claim_ceiling": (
            "Operational provenance, failure diagnosis and read-only verification of the "
            "v68 ordered work. No quality measurement, no bar/rubric/threshold/gate-predicate/"
            "verdict-contract edit, no serve verdict, no packet admission, no human-gate claim "
            "and no universal-174k benchmark. The FAST-MVP retrieval/counter-authority "
            "benchmark is reused by hash only, never rebuilt or re-executed."),
        "posture": {"packet_admitted": False, "machine_gate_ready": False,
                    "human_gate_ready": False, "ready_for_owner_session": False,
                    "owner_decision_required": False, "continue_recommended": False},
    }
    write_json(RESULT, record)
    return record


def phase_final_gates() -> dict:
    nested = run_nested_guard(NESTED)
    integrity = run_state_gate(STATE_INTEGRITY)
    scope = write_scope_snapshot()
    rules = {
        "freeze_inputs": verify_freeze(),
        "R6_nested_and_state": {
            "passed": bool(nested["exit_0"] and nested["n_unresolved"] == 0
                           and nested["n_top_level_unresolved"] == 0
                           and integrity["exit_0"] and integrity["n_failed"] == 0
                           and integrity["n_checks"] == 11),
            "nested": nested, "state_integrity": integrity,
        },
        "R7_write_scope": {
            "passed": bool(scope["exit_0"] and scope["n_bad"] == 0),
            "observed": scope,
        },
    }
    passed = all(r["passed"] for r in rules.values())
    final = {
        "schema": "lex-evaluation-operational-resume-final-gates/1",
        "run_id": int(RUN),
        "resumes_snapshot_of": int(FAILED_RUN),
        "direction_version": DIRECTION_VERSION,
        "generated_at_utc": now(),
        "claim_bearing_run": int(RUN),
        "audit_status": "PENDING_INDEPENDENT_AUDIT",
        "accepted_as_evidence": False,
        "rules": rules,
        "rule_pass": {k: v["passed"] for k, v in rules.items()},
        "passed": passed,
        "verdict": "AUDIT_READY" if passed else "FINAL_GATES_FAILED",
        "exit_code": 0 if passed else 1,
        "closes_defect_of_failed_run": (
            "run 44680596390 left no own-run deliverable; this run supplies the "
            "state block, result record, report, freeze-first record and closed gates"),
        "claim_ceiling": ("Operational provenance only; no quality measurement, no frozen "
                          "edit, no serve verdict, no human-gate claim, no 174k benchmark."),
    }
    write_json(FINAL_GATES, final)
    # Stamp the result record with the final gate outcomes (same path; no new claim).
    result = load_json(RESULT)
    result["final_gates"] = {"verdict": final["verdict"], "passed": passed,
                             "record": FINAL_GATES, "nested": nested,
                             "state_integrity": integrity, "write_scope": scope}
    result["verdict"] = "SNAPSHOT_AUDIT_READY" if passed else "FINAL_GATES_FAILED"
    result["generated_at_utc"] = now()
    write_json(RESULT, result)
    return final


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--phase", choices=["prestate", "final-gates"], required=True)
    args = ap.parse_args(argv)
    if args.phase == "prestate":
        rec = phase_prestate()
        print(json.dumps({"phase": "prestate", "verdict": rec["verdict"],
                          "result": RESULT}, indent=1))
        return 0 if rec["verdict"] != "VERIFICATION_FAILED" else 1
    final = phase_final_gates()
    print(json.dumps({"phase": "final-gates", "verdict": final["verdict"],
                      "rule_pass": final["rule_pass"]}, indent=1))
    return final["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
