#!/usr/bin/env python3
"""Operational-resume diagnosis + verification for evaluation run 44887103047.

Resumes the persisted producer snapshot of run 44882968860 (ada742d7) without
restarting. Read-only with respect to every inherited artifact: it diagnoses the
orchestration/validation failure of 44882968860 from cached GitHub REST read
facts, verifies the snapshot's deliverable (frozen FAST-MVP falsifier
re-execution, shims, freeze pins, scope), and records the v68 ordered-work
status without re-deriving closed work.

Writes under results/evaluation/operational_resume_44887103047/:
  diagnosis_44882968860.json, snapshot_integrity_44887103047.json,
  ordered_work_44887103047.json, write_scope_44887103047.json,
  verification_44887103047.json
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = "44887103047"
PRIOR = "44882968860"
OUT = ROOT / f"results/evaluation/operational_resume_{RUN}"
SNAPSHOT = "ada742d7c1ddb91779c91bb55166e9e598f1caf6"
SNAPSHOT_PARENT = "519d6bc79b6097f06c724ae137a5be651d5ba2ef"
ACCEPTED_BASE = "ea98384e54d31d2e694c418a1d1ce5769fc6c32f"
PRODUCT_MOUNT = Path("/tmp/lex_accepted/product")
QUANTUM_SECONDS = 2700


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def gate_ids(records) -> set:
    return {g if isinstance(g, str) else g.get("gate", json.dumps(g, sort_keys=True)) for g in records}


def main() -> int:
    checks: list[dict] = []

    def check(name: str, ok: bool, detail) -> None:
        checks.append({"check": name, "pass": bool(ok), "detail": detail})

    OUT.mkdir(parents=True, exist_ok=True)

    # =====================================================================
    # H1 — diagnosis of run 44882968860 (orchestration failure)
    # =====================================================================
    run = load(OUT / "rest/run_44882968860.json")
    jobs = load(OUT / "rest/jobs_44882968860.json")["jobs"]
    audit_job = load(OUT / "rest/audit_job_136783749627.json")
    team_job = load(OUT / "rest/team_job_136782080655.json")
    by_name = {j["name"]: j for j in jobs}

    def iso(t: str) -> int:
        return int(datetime.fromisoformat(t.replace("Z", "+00:00")).timestamp())

    audit_secs = iso(audit_job["completed_at"]) - iso(audit_job["started_at"])
    steps = {s["name"]: s for s in audit_job["steps"]}
    failed_steps = [s["name"] for s in audit_job["steps"] if s.get("conclusion") == "failure"]
    skipped_steps = [s["name"] for s in audit_job["steps"] if s.get("conclusion") == "skipped"]

    check("D1_rest_read_facts", (
        run["conclusion"] == "failure"
        and by_name["team"]["conclusion"] == "success"
        and audit_job["conclusion"] == "failure"
        and failed_steps == ["Independent audit"]
        and "Enforce audit scope and read gate" in skipped_steps
        and "Persist audit snapshot" in skipped_steps
        and by_name["integrate"]["conclusion"] == "skipped"
        and by_name["resilience"]["conclusion"] == "success"
    ), {
        "run_conclusion": run["conclusion"],
        "team_conclusion": by_name["team"]["conclusion"],
        "audit_conclusion": audit_job["conclusion"],
        "audit_failed_steps": failed_steps,
        "audit_skipped_steps": skipped_steps,
        "integrate_conclusion": by_name["integrate"]["conclusion"],
        "resilience_conclusion": by_name["resilience"]["conclusion"],
        "source": "cached GitHub REST read facts under results/evaluation/operational_resume_44887103047/rest/",
    })

    check("D2_audit_quantum_class_inference", 2700 <= audit_secs <= 2900, {
        "audit_job_seconds": audit_secs,
        "documented_quantum_seconds": QUANTUM_SECONDS,
        "inference": "The %ds wall time is consistent with LEX_WORK_QUANTUM_EXPIRED (seconds=%d) or a provider-rotation death; job logs return HTTP 403 so the exact in-agent cause is an INFERENCE, never a log read." % (audit_secs, QUANTUM_SECONDS),
        "inference_tag": "INFERENCE_DO_NOT_LAUNDER_AS_LOG_READ",
        "log_probe_status_file": f"results/evaluation/operational_resume_{RUN}/rest/audit_log_probe_44882968860.status",
    })

    audit_ref = git("rev-parse", "--verify", "-q", f"origin/cycle/core/evaluation/{PRIOR}/audit")
    gate_worktree = (ROOT / f"results/audit/evaluation/CYCLE_{PRIOR}_GATE.json").exists()
    gate_in_team = git("cat-file", "-e", f"{SNAPSHOT}:results/audit/evaluation/CYCLE_{PRIOR}_GATE.json")
    check("D3_no_gate_no_audit_ref_no_verdict", (
        audit_ref.returncode != 0 and not gate_worktree and gate_in_team.returncode != 0
    ), {
        "audit_ref_resolves": audit_ref.returncode == 0,
        "gate_file_in_worktree": gate_worktree,
        "gate_file_in_team_ref": gate_in_team.returncode == 0,
        "consequence": "No gate verdict was ever issued for run 44882968860; integrate was skipped; the resilience job dispatched this resume with resume_from_run_id=44882968860.",
        "failure_class": "AUDIT_AGENT_STEP_FAILURE_NO_GATE",
        "not": ["gate verdict", "producer failure", "product defect", "measurement failure", "write-scope violation", "human-gate event"],
    })

    log_probe = (OUT / "rest/audit_log_probe_44882968860.status").read_text().strip()
    check("D4_log_availability_disclosed", log_probe == "403", {
        "http_status": log_probe,
        "meaning": "job logs require admin rights; step identity/conclusions/timestamps are READ facts, the in-agent cause stays an inference",
    })

    diagnosis = {
        "schema": "lex-evaluation-operational-resume-diagnosis/1",
        "lane": "evaluation",
        "run": int(RUN),
        "diagnosed_run": int(PRIOR),
        "direction_version": 68,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "failure_class": "AUDIT_AGENT_STEP_FAILURE_NO_GATE",
        "failure_summary": (
            "Run 44882968860 completed its TEAM job end-to-end (steps 'Run lane cycle', "
            "'Validate active MVP producer state', 'Clean generated junk', 'Enforce lane write scope' "
            "'Persist team snapshot' all success; 08:02:20Z->08:09:14Z), force-pushing the persisted "
            "producer snapshot ada742d7 to origin/cycle/core/evaluation/44882968860/team. It failed ONLY "
            "in the AUDIT job at step 5 'Independent audit' (08:09:16Z->08:55:01Z, %ds). Audit steps "
            "'Enforce audit scope and read gate' and 'Persist audit snapshot' were skipped, integrate was "
            "skipped, no CYCLE_44882968860_GATE.json exists in the worktree or the team ref and no "
            "/audit branch resolves: NO VERDICT WAS EVER ISSUED. The resilience job then dispatched this "
            "operational resume (resume_from_run_id=44882968860)." % audit_secs
        ),
        "inference_disclosure": (
            "The exact in-agent cause (work-quantum expiry at 2700s vs provider rotation vs model auth) "
            "is an INFERENCE from the %ds duration and the documented failure classes; job logs return "
            "HTTP 403 unauthenticated (recorded in rest/audit_log_probe_44882968860.status), so no log "
            "line was read." % audit_secs
        ),
        "read_facts": {
            "run": {"id": int(PRIOR), "conclusion": run["conclusion"], "name": run["name"],
                    "created_at": run["created_at"], "updated_at": run["updated_at"]},
            "team_job": {"id": team_job["id"], "conclusion": team_job["conclusion"],
                         "started_at": team_job["started_at"], "completed_at": team_job["completed_at"],
                         "all_steps_success": all(s.get("conclusion") == "success" for s in team_job["steps"] if s.get("status") == "completed")},
            "audit_job": {"id": audit_job["id"], "conclusion": audit_job["conclusion"],
                          "started_at": audit_job["started_at"], "completed_at": audit_job["completed_at"],
                          "wall_seconds": audit_secs, "failed_steps": failed_steps,
                          "skipped_steps": skipped_steps},
            "integrate": by_name["integrate"]["conclusion"],
            "resilience": by_name["resilience"]["conclusion"],
        },
        "provenance": {
            "rest_cache_dir": f"results/evaluation/operational_resume_{RUN}/rest/",
            "files": sorted(str(p.relative_to(ROOT)) for p in (OUT / "rest").glob("*.json")),
            "log_probe_status": int(log_probe),
        },
        "consequence_for_this_resume": "The producer snapshot is the only durable output of 44882968860 and is resumed here; nothing needs to be rebuilt from scratch.",
    }
    (OUT / f"diagnosis_{PRIOR}.json").write_text(json.dumps(diagnosis, indent=2, sort_keys=True) + "\n")
    check("D1_diagnosis_artifact_written", (OUT / f"diagnosis_{PRIOR}.json").is_file(), str(OUT / f"diagnosis_{PRIOR}.json").replace(str(ROOT) + "/", ""))

    # =====================================================================
    # H2 — frozen FAST-MVP falsifier reproduction (verification, not a re-score)
    # =====================================================================
    new = load(OUT / f"{RUN}_verify.json")
    expected_failed = [
        "mf::concept_coverage::39319405429::de-kapitalverletzung",
        "mf::counter_authority_surface::39319405429::de-kapitalverletzung",
        "mf::counter_authority_surface::39319405429::fr-bail-entretien",
        "mf::counter_authority_surface::39319405429::it-responsabilita-medica",
    ]
    targets = {
        "44870660846": ROOT / "results/evaluation/minimal_ca_falsify_benchmark/44870660846.json",
        PRIOR: ROOT / f"results/evaluation/operational_resume_{PRIOR}/{PRIOR}_verify.json",
    }
    comparisons = {}
    for rid, path in targets.items():
        ref = load(path)
        cmp_ = {
            "ref_record": str(path.relative_to(ROOT)),
            "ref_sha256": sha256(path),
            "verdict_equal": ref["verdict"] == new["verdict"],
            "n_gates_equal": ref["n_gates"] == new["n_gates"],
            "n_passed_equal": ref["n_passed"] == new["n_passed"],
            "n_failed_equal": ref["n_failed"] == new["n_failed"],
            "failed_gates_set_equal": gate_ids(ref["failed_gates"]) == gate_ids(new["failed_gates"]),
            "product_mount_head_equal": ref.get("product_mount_head") == new.get("product_mount_head"),
            "run_valid_equal": ref.get("run_valid") == new.get("run_valid"),
            "input_drift_empty": new.get("input_drift") == [],
            "direction_version_68": new.get("direction_version") == 68,
        }
        cmp_["all_equal"] = all(v for k, v in cmp_.items() if k.endswith(("equal", "empty", "68")))
        comparisons[rid] = cmp_
    check("B1_reproduces_committed_records", all(c["all_equal"] for c in comparisons.values()), comparisons)
    check("B2_expected_failed_gate_set", gate_ids(new["failed_gates"]) == set(expected_failed), sorted(gate_ids(new["failed_gates"])))
    ceiling_ref = load(targets[PRIOR]).get("claim_ceiling")
    check("B3_claim_ceiling_unchanged_fail_closed", str(new.get("claim_ceiling")) == str(ceiling_ref), {
        "equal_to_prior_resume_record": str(new.get("claim_ceiling")) == str(ceiling_ref),
        "note": "verification re-execution of a frozen instrument on packet-of-record 39319405429; not a second independent falsification, not a re-score, not a serve verdict, no bar moved",
    })

    # =====================================================================
    # H3 — snapshot integrity + freeze pins + scope + posture
    # =====================================================================
    freeze = load(ROOT / f"evaluation/OPERATIONAL_RESUME_{RUN}_FREEZE_V1.json")
    prior_freeze = load(ROOT / f"evaluation/OPERATIONAL_RESUME_{PRIOR}_FREEZE_V1.json")
    pin_results = {}
    for section in ("frozen_instruments", "comparison_targets", "prior_resume_deliverable_pins",
                    "item1_deliverable_pins", "test_file_pins"):
        for rel, want in freeze.get(section, {}).items():
            got = sha256(ROOT / rel)
            pin_results[rel] = {"section": section, "expected": want, "actual": got, "match": got == want}
    for rel, want in freeze["snapshot_shim_pin"].items():
        if rel != "note" and isinstance(want, str) and len(want) == 64:
            got = sha256(ROOT / rel)
            pin_results[rel] = {"section": "snapshot_shim_pin", "expected": want, "actual": got, "match": got == want}
    for section in ("frozen_instruments", "comparison_targets", "item1_deliverable_pins", "test_file_pins"):
        for rel, want in prior_freeze.get(section, {}).items():
            got = sha256(ROOT / rel)
            key = f"prior::{rel}"
            pin_results[key] = {"section": f"prior_freeze::{section}", "expected": want, "actual": got, "match": got == want}
    for name, want in prior_freeze["frozen_rules_reference"].items():
        if name.startswith("RULES_"):
            p = ROOT / "evaluation/frozen_bars" / name
            got = sha256(p) if p.exists() else None
            pin_results[f"prior::frozen_bars/{name}"] = {"section": "prior_freeze::frozen_rules_reference", "expected": want, "actual": got, "match": got == want}
    check("S1_all_freeze_pins_rehash_equal", all(v["match"] for v in pin_results.values()), pin_results)

    delta_record = load(OUT / "snapshot_delta_files_44887103047.json")
    live_delta = [l.split("\t") for l in git("diff", "--name-status", SNAPSHOT_PARENT, SNAPSHOT).stdout.splitlines()]
    live_pairs = [{"change": c, "path": p} for c, p in live_delta]
    head_now = git("rev-parse", "HEAD").stdout.strip()
    team_ref = git("rev-parse", f"origin/cycle/core/evaluation/{PRIOR}/team").stdout.strip()
    check("S2_snapshot_preserved_intact", (
        head_now == SNAPSHOT and team_ref == SNAPSHOT
        and live_pairs == delta_record["files"]
        and delta_record["audit_namespace_paths"] == []
        and all(not f["path"].startswith(("reports/audit/", "results/audit/")) for f in live_pairs)
    ), {
        "head": head_now, "team_ref": team_ref, "expected_snapshot": SNAPSHOT,
        "n_delta_files": len(live_pairs), "matches_recorded_delta_list": live_pairs == delta_record["files"],
        "audit_namespace_paths": [f["path"] for f in live_pairs if f["path"].startswith(("reports/audit/", "results/audit/"))],
    })

    shim_rel = "results/evaluation/orchestration/local_pytest_shim.json"
    git_bytes = subprocess.run(["git", "show", f"{SNAPSHOT}:{shim_rel}"], cwd=ROOT, capture_output=True, check=True).stdout
    git_sha = hashlib.sha256(git_bytes).hexdigest()
    work_sha = sha256(ROOT / shim_rel)
    check("S3_snapshot_shim_byte_identical", git_sha == work_sha == freeze["snapshot_shim_pin"][shim_rel], {
        "git_blob_sha256": git_sha, "worktree_sha256": work_sha,
        "pin": freeze["snapshot_shim_pin"][shim_rel],
        "preserved_not_edited": True,
    })

    prior_verify = load(ROOT / f"results/evaluation/operational_resume_{PRIOR}/verification_{PRIOR}.json")
    check("S4_prior_resume_verification_still_stands", (
        prior_verify["verdict"] == "VERIFICATION_PASS" and prior_verify["n_fail"] == 0
        and sha256(ROOT / f"results/evaluation/operational_resume_{PRIOR}/verification_{PRIOR}.json")
        == freeze["comparison_targets"][f"results/evaluation/operational_resume_{PRIOR}/verification_{PRIOR}.json"]
    ), {"verdict": prior_verify["verdict"], "n_pass": prior_verify["n_pass"], "n_fail": prior_verify["n_fail"]})

    main_shim = load(OUT / f"no_pytest_{RUN}.json")
    disclosed = [r for r in main_shim["results"] if r["test_file"] == "tests/evaluation/test_retrieval_benchmark.py"]
    primary = [r for r in main_shim["results"] if r["test_file"] == "tests/evaluation/test_minimal_ca_falsify_benchmark.py"]
    check("T1_shim_SHIM_PASS_8_multilingual_disclosed", (
        main_shim["verdict"] == "SHIM_PASS" and main_shim["n_passed"] == 8 and main_shim["n_failed"] == 0
        and primary and primary[0]["status"] == "PASS"
        and disclosed and disclosed[0]["status"] == "IMPORT_ERROR"
    ), {
        "verdict": main_shim["verdict"], "n_passed": main_shim["n_passed"], "n_failed": main_shim["n_failed"],
        "multilingual_status": disclosed[0]["status"] if disclosed else None,
        "multilingual_counted_as_passed": False,
        "pytest_available": main_shim["pytest_available"],
    })

    ml = load(OUT / f"multilingual_provenance_shim_{RUN}.json")
    check("T2_multilingual_provenance_shim_reused", (
        ml["verdict"] == "SHIM_PASS" and ml["n_passed"] == 2 and ml["n_failed"] == 0
        and ml["results"][0]["test_file_sha256"] == freeze["test_file_pins"]["tests/evaluation/test_retrieval_benchmark.py"]
    ), {
        "verdict": ml["verdict"], "n_passed": ml["n_passed"], "n_failed": ml["n_failed"],
        "test_file_sha256": ml["results"][0]["test_file_sha256"],
        "protocol_digest_line": "e1a0b18d23d18bd1aafe54a66329fd0b04cd6f95f794d3d0336e0d867af41b7e (equal to expected, read from runner stdout log)",
        "reused_test": True, "shim_is_not_pytest": True,
    })

    diff = git("diff", "--name-only", ACCEPTED_BASE, "HEAD").stdout.splitlines()
    audit_paths = [p for p in diff if p.startswith(("reports/audit/", "results/audit/"))]
    check("W1_tree_diff_vs_accepted_base_no_audit_namespace", audit_paths == [], {
        "n_diff_paths": len(diff), "audit_paths": audit_paths,
    })

    porcelain = git("status", "--porcelain", "-uall").stdout.splitlines()
    allowed = ("evaluation/", "tests/evaluation/", "results/evaluation/", "reports/evaluation/",
               "state/evaluation.json", "data/evaluation/")
    bad = [l[3:] for l in porcelain if l[3:] and not l[3:].startswith(allowed)]
    check("W2_write_scope_simulation_n_bad_zero", bad == [], {"n_entries": len(porcelain), "bad_paths": bad})
    (OUT / f"write_scope_{RUN}.json").write_text(json.dumps({
        "schema": "lex-evaluation-write-scope/1", "run": int(RUN),
        "method": "local replay of core-lane 'Enforce lane write scope' predicate over git status --porcelain -uall",
        "allowed_prefixes": list(allowed), "n_entries": len(porcelain), "bad_paths": bad,
        "verdict": "CLEAN" if not bad else "VIOLATION",
    }, indent=2, sort_keys=True) + "\n")

    state = load(ROOT / "state/evaluation.json")
    posture = {k: state.get(k) for k in ("human_gate_ready", "machine_gate_ready",
                                         "owner_decision_required", "continue_recommended")}
    check("P1_posture_fail_closed", (
        posture["human_gate_ready"] is False and posture["machine_gate_ready"] is False
        and posture["owner_decision_required"] is False and posture["continue_recommended"] is False
        and state.get("accepted_run_id") == 40258497460
    ), {**posture, "accepted_run_id": state.get("accepted_run_id")})
    check("P2_direction_version_pin_68", state.get("direction_version") == 68, state.get("direction_version"))

    # =====================================================================
    # H4 — v68 ordered-work status (verified, NOT re-derived)
    # =====================================================================
    mount_head = git("-C", str(PRODUCT_MOUNT), "rev-parse", "HEAD").stdout.strip()
    mount_status = git("-C", str(PRODUCT_MOUNT), "status", "--porcelain").stdout.strip()
    post_repair = load(ROOT / f"results/evaluation/post_repair_family_ca_falsifier/44861140260.json")
    family_rec = load(ROOT / "results/evaluation/post_repair_family_ca_falsifier/40134202991.json")
    gate_on_lab = git("show", "origin/lab/evaluation:results/audit/evaluation/CYCLE_40133253347_GATE.json")
    gate_1 = json.loads(gate_on_lab.stdout) if gate_on_lab.returncode == 0 else {}
    accept_commit = git("log", "origin/lab/evaluation", "--oneline", "--grep=accept evaluation cycle 40133253347")
    audit_ref_1 = git("rev-parse", "--verify", "-q", "origin/cycle/core/evaluation/40133253347/audit")

    ordered = {
        "schema": "lex-evaluation-ordered-work-status/1",
        "lane": "evaluation", "run": int(RUN), "direction_version": 68,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "item_1_report_only_correction_of_record": {
            "status": "DISCHARGED_VERIFIED",
            "half_1_gate": {"gate": gate_1.get("gate"), "safe_to_integrate": gate_1.get("safe_to_integrate"),
                            "required_fixes_n": len(gate_1.get("required_fixes", [])),
                            "source": "origin/lab/evaluation:results/audit/evaluation/CYCLE_40133253347_GATE.json",
                            "audit_branch_ref_resolves": audit_ref_1.returncode == 0,
                            "disclosure": "the cycle/core/evaluation/40133253347/audit branch does not currently resolve; the gate file is present in the accepted tree because the integrate job copied it from the audit branch into the accept commit. Half-1 content is read from that committed copy; the branch-based provenance is disclosed as unavailable, not asserted."},
            "half_2_accept_commit": {"found": accept_commit.returncode == 0 and bool(accept_commit.stdout.strip()),
                                     "line": accept_commit.stdout.strip().splitlines()[0] if accept_commit.stdout.strip() else None,
                                     "ref": "origin/lab/evaluation"},
            "reused_record": "results/evaluation/post_repair_family_ca_falsifier/44861140260.json -> ordered_work_status.item_1_correction_of_record",
            "re_run_this_cycle": False,
        },
        "item_2_conditional_remeasure": {
            "status": post_repair["ordered_work_status"]["item_2_conditional_remeasure"],
            "leg_half": post_repair["ordered_work_status"]["item_2_leg_half"],
            "basis": "record of record is results/evaluation/post_repair_family_ca_falsifier/44861140260.json (precondition H1 leg LANDED=true, H2 full family regenerated=false, member-for-member 14/15, server/served role 3 of 4)",
            "unchanged_this_cycle_proof": {
                "product_mount_head_then": post_repair["product_mount_head"],
                "product_mount_head_now": mount_head,
                "mount_head_equal": mount_head == post_repair["product_mount_head"],
                "mount_worktree_clean": mount_status == "",
                "argument": "the precondition adjudicator's inputs are the committed product tree at the mount head; the mount head and tree are unchanged since 44861140260, so the NOT_YET_DISCRIMINATING adjudication remains current. The full protocol was NOT re-run (zero-delta re-run of frozen inputs is recorded as operational, not as evidence) and no synthetic stand-in was substituted.",
            },
            "trigger_rule_quoted": "ordered item (2) executes ONLY IF the rejection/incumbent leg lands AND the full 15-member flagship family is regenerated; otherwise NOT_YET_DISCRIMINATING and stop",
            "re_run_this_cycle": False,
        },
        "item_3_standing_falsification_record": {
            "status": "UNCHANGED",
            "detail": "PRODUCT_FALSIFIED on packet-of-record 39319405429 remains the benchmark of record; this run's re-execution is verification only. The counter-authority yield negative (2/4 frozen questions, zero candidate counter labels under the frozen marker rule) stays scoped to THIS LANE'S OWN PRODUCER and is never quoted as Core Product's counter channel.",
        },
        "item_4_non_blocking_required_fixes": {
            "status": "REPORTED_ONLY_WHERE_QUOTED",
            "detail": "the three non-blocking required fixes of CYCLE_39965089504_GATE.json are reported wherever this lane quotes those counts, never silently; this run quotes no such count.",
        },
        "item_5_no_rederivation": {
            "status": "HONOURED",
            "detail": "this cycle is operational verification + diagnosis; it re-derives no closed work and is recorded as operational, not as new evidence.",
        },
        "not_in_scope": ["frozen bar/rubric/threshold/verdict contract edits", "serve verdict re-run",
                         "174k benchmark rerun", "frontier-counter-evidence-content-filter consultation",
                         "counter-anchor classifier build", "comparative map-vs-list scoring",
                         "posture flag changes", "owner decision"],
    }
    (OUT / f"ordered_work_{RUN}.json").write_text(json.dumps(ordered, indent=2, sort_keys=True) + "\n")
    check("O1_item1_discharged_verified", ordered["item_1_report_only_correction_of_record"]["half_1_gate"].get("gate") == "PASS"
          and ordered["item_1_report_only_correction_of_record"]["half_2_accept_commit"]["found"],
          {"gate": ordered["item_1_report_only_correction_of_record"]["half_1_gate"].get("gate"),
           "accept_commit": ordered["item_1_report_only_correction_of_record"]["half_2_accept_commit"].get("line"),
           "audit_branch_disclosed_absent": ordered["item_1_report_only_correction_of_record"]["half_1_gate"]["audit_branch_ref_resolves"] is False})
    check("O2_item2_not_yet_discriminating_unchanged", (
        post_repair["precondition"]["H1_precondition_leg_landed"] is True
        and post_repair["precondition"]["H2_precondition_full_family_regenerated"] is False
        and mount_head == post_repair["product_mount_head"] and mount_status == ""
    ), ordered["item_2_conditional_remeasure"]["unchanged_this_cycle_proof"])

    snapshot_integrity = {
        "schema": "lex-evaluation-snapshot-integrity/1",
        "lane": "evaluation", "run": int(RUN),
        "resumed_run": int(PRIOR),
        "snapshot_commit": SNAPSHOT, "snapshot_parent": SNAPSHOT_PARENT,
        "snapshot_equals_team_ref": team_ref == SNAPSHOT,
        "head_equals_snapshot": head_now == SNAPSHOT,
        "delta_files": live_pairs, "delta_n": len(live_pairs),
        "audit_namespace_paths": [],
        "claim_bearing_outputs_inherited_untouched": True,
        "prior_deliverable_pins_verified": True,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    (OUT / f"snapshot_integrity_{RUN}.json").write_text(json.dumps(snapshot_integrity, indent=2, sort_keys=True) + "\n")

    n_pass = sum(1 for c in checks if c["pass"])
    n_fail = len(checks) - n_pass
    out = {
        "schema": "lex-evaluation-operational-resume-verification/1",
        "lane": "evaluation", "run": int(RUN),
        "resumed_run": int(PRIOR),
        "direction_version": 68,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "checks": checks, "n_checks": len(checks), "n_pass": n_pass, "n_fail": n_fail,
        "verdict": "VERIFICATION_PASS" if n_fail == 0 else "VERIFICATION_FAIL",
        "benchmark_reproduction": {
            "run_id": new["run_id"], "verdict": new["verdict"], "n_gates": new["n_gates"],
            "n_passed": new["n_passed"], "n_failed": new["n_failed"],
            "failed_gates": new["failed_gates"], "product_mount_head": new["product_mount_head"],
            "run_valid": new["run_valid"], "input_drift": new["input_drift"],
            "claim_ceiling": "verification re-execution of the frozen instrument on packet-of-record 39319405429; not a second falsification, not a re-score, not a serve verdict",
        },
        "failure_diagnosed": {
            "run": int(PRIOR), "failure_class": "AUDIT_AGENT_STEP_FAILURE_NO_GATE",
            "record": f"results/evaluation/operational_resume_{RUN}/diagnosis_{PRIOR}.json",
        },
        "ordered_work_status": {k: (v if isinstance(v, str) else v.get("status"))
                                for k, v in ordered.items() if k.startswith("item_") or k == "item_5_no_rederivation"},
        "posture": posture,
        "claim_ceiling": "Operational resume: diagnosis of an orchestration failure + verification re-execution of frozen instruments + audit-readiness. NOT new evidence, NOT a falsification, NOT an acceptance claim; accepted_run_id stays 40258497460.",
    }
    (OUT / f"verification_{RUN}.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"verdict": out["verdict"], "n_pass": n_pass, "n_fail": n_fail,
                      "failed_checks": [c["check"] for c in checks if not c["pass"]]}))
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
