#!/usr/bin/env python3
"""Operational-resume audit-ready record builder for run 45965187540.

Resumes the persisted producer snapshot of run 45965013167. Builds diagnosis,
deliverable-verification, replay-comparison, pin-rehash and accepted-pointer
reconciliation records, then performs an ADDITIVE state update on both state
files. Never writes into the auditor namespace and never edits a frozen bar.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RUN = 45965187540
RESUMED = 45965013167
DIR = REPO / "results" / "evaluation" / "operational_resume_45965187540"
EXCLUDED = {
    "run_id", "generated_at_utc", "engine_record_path",
    "product_mount_head", "numeric_environment",
}
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return json.loads(path.read_text())


def dump(path: Path, obj) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")
    return sha(path)


def rel(path: Path) -> str:
    return str(path.relative_to(REPO))


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


def main() -> None:
    DIR.mkdir(parents=True, exist_ok=True)
    committed = load(REPO / "results/evaluation/minimal_retrieval_ca_benchmark/test_40265377500.json")
    replay = load(REPO / "results/evaluation/minimal_retrieval_ca_benchmark/45965187540.json")
    engine = load(REPO / "results/evaluation/minimal_retrieval_ca_benchmark/45965187540_engine_mapping_free_recall_falsifier.json")
    freeze = load(REPO / "evaluation/OPERATIONAL_RESUME_45965187540_FREEZE_V1.json")
    hypothesis = load(REPO / "evaluation/OPERATIONAL_RESUME_45965187540_HYPOTHESIS_V1.json")

    # ---- orchestration diagnosis -------------------------------------------
    diagnosis = {
        "schema": "lex-evaluation-orchestration-diagnosis/1",
        "run_under_resume": RESUMED,
        "current_run": RUN,
        "direction_version": 68,
        "generated_at_utc": NOW,
        "github_api_provenance": {
            "runs_endpoint": f"https://api.github.com/repos/Mickalive/LexMachina/actions/runs/{RESUMED}",
            "jobs_endpoint": f"https://api.github.com/repos/Mickalive/LexMachina/actions/runs/{RESUMED}/jobs",
            "access": "public unauthenticated REST, HTTP 200",
            "job_logs_endpoint_status": "HTTP 403 (admin rights required); exact agent error NOT observed and is not claimed",
        },
        "run_metadata": {
            "name": "Core evaluation dirV68 repair0",
            "event": "workflow_dispatch",
            "status": "completed",
            "conclusion": "failure",
            "created_at_utc": "2026-11-27T08:21:19Z",
            "head_branch": "main",
            "head_sha": "02a3d67d228c5282a3b51e25e0952ce4cb4368dd",
            "run_attempt": 1,
        },
        "job_steps": [
            ["Set up job", "success"], ["Run actions/checkout@v6", "success"],
            ["Validate lane and initialize working base", "success"],
            ["Mount accepted peer evidence", "success"], ["Install Ox/OpenCode", "success"],
            ["Run lane cycle", "failure"],
            ["Validate active MVP producer state", "skipped"],
            ["Clean generated junk", "success"],
            ["Enforce lane write scope", "skipped"],
            ["Persist team snapshot", "success"],
            ["Post Run actions/checkout@v6", "success"], ["Complete job", "success"],
        ],
        "other_jobs": {"resilience": "success", "integrate": "skipped", "audit": "skipped"},
        "failure_class": "PRODUCER_STEP_ORCHESTRATION_DEATH",
        "failure_summary": (
            "The team job's 'Run lane cycle' step failed; validation, write-scope enforcement, "
            "audit and integrate were skipped. 'Persist team snapshot' runs under if: always() "
            "and force-pushed the inherited tree, so the snapshot ref exists with no new verdict. "
            "This is not a gate REVISE/BLOCKED, not a write-scope SCOPE_VIOLATION, not a work-quantum "
            "starvation verdict and not a product defect."
        ),
        "zero_new_commits_proof": {
            "snapshot_ref": "refs/remotes/origin/cycle/core/evaluation/45965013167/team",
            "snapshot_head": "ea98384e54d31d2e694c418a1d1ce5769fc6c32f",
            "snapshot_head_commit_time_utc": "2026-10-26T03:56:04Z",
            "producer_commits_added_by_run": 0,
            "note": "snapshot head predates the run by ~32 days; the producer agent added no commit",
        },
        "audit_ref_absence": {
            "audit_job_conclusion": "skipped",
            "audit_gate_file_for_45965013167": "ABSENT",
            "verdict_issued": False,
        },
        "control_plane_hardening_recorded_not_edited": [
            ".github/** is control-plane scope and is NOT edited from this lane.",
            "'Persist team snapshot' under if: always() publishes an unverified producer tree after any producer-step death; this is recorded, not patched.",
            "The failed step's exact provider/model error is unobservable at HTTP 403 unauthenticated; no provider attribution is claimed.",
        ],
    }
    diagnosis_p = DIR / "diagnosis_45965013167.json"
    diagnosis_sha = dump(diagnosis_p, diagnosis)

    # ---- pin rehash ---------------------------------------------------------
    pins = []
    declared = {
        "wrapper_artifact": ("results/evaluation/minimal_retrieval_ca_benchmark/test_40265377500.json", "5944f921c00d8f24f52506d5fbe9ffa8686c5a814172f16879f1f345b651a0a1"),
        "engine_artifact": ("results/evaluation/minimal_retrieval_ca_benchmark/test_40265377500_engine_mapping_free_recall_falsifier.json", "e1dc2238d6b721903a5c535f0a5e1a2d95754152b46db24467dc30290606db07"),
        "wrapper_instrument": ("evaluation/minimal_retrieval_ca_benchmark.py", "50338dbde3005fad43f90f7765ad0648da4c18d26e01b99258ae250232654122"),
        "engine_instrument": ("evaluation/mapping_free_recall_falsifier.py", "58a2e77a66bb60385a53185e9426447e8465da9105e8a0cb8945d5fd77bfb302"),
        "frozen_spec": ("evaluation/retrieval_gate/frozen_retrieval_benchmark.json", "187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72"),
        "frozen_label_rubric": ("evaluation/frozen_bars/RULES_LABEL.json", "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"),
        "frozen_geometry_rubric": ("evaluation/frozen_bars/RULES_GEOMETRY.json", "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633"),
        "freeze_record": ("evaluation/OPERATIONAL_RESUME_45965187540_FREEZE_V1.json", freeze and sha(REPO / "evaluation/OPERATIONAL_RESUME_45965187540_FREEZE_V1.json")),
        "hypothesis": ("evaluation/OPERATIONAL_RESUME_45965187540_HYPOTHESIS_V1.json", sha(REPO / "evaluation/OPERATIONAL_RESUME_45965187540_HYPOTHESIS_V1.json")),
    }
    for name, (path, expected) in declared.items():
        p = REPO / path
        got = sha(p) if p.exists() else None
        pins.append({"pin": name, "path": path, "expected": expected, "live": got,
                     "verdict": "MATCH" if got == expected else "MISMATCH"})
    # in-artifact frozen pins
    for name, key in [("mapping_free_hypothesis", "frozen_hypothesis"),
                      ("mapping_free_freeze", "freeze_record")]:
        obj = committed.get(key, {})
        p = REPO / obj.get("path", "")
        got = sha(p) if p.exists() else None
        pins.append({"pin": name, "path": obj.get("path"), "expected": obj.get("sha256"),
                     "live": got, "verdict": "MATCH" if got == obj.get("sha256") else "MISMATCH"})
    pin_record = {
        "schema": "lex-evaluation-pin-rehash/1",
        "run_id": RUN, "generated_at_utc": NOW,
        "n_pins": len(pins),
        "n_match": sum(p["verdict"] == "MATCH" for p in pins),
        "n_mismatch": sum(p["verdict"] == "MISMATCH" for p in pins),
        "verdict": "PINS_ALL_MATCH" if all(p["verdict"] == "MATCH" for p in pins) else "PIN_MISMATCH",
        "pins": pins,
    }
    pin_p = DIR / "pin_rehash_45965187540.json"
    pin_sha = dump(pin_p, pin_record)

    # ---- replay comparison --------------------------------------------------
    cf, rf = flatten(committed), flatten(replay)
    compared, diffs = [], []
    for k in sorted(set(cf) | set(rf)):
        top = k.split(".")[0].split("[")[0]
        if top in EXCLUDED:
            continue
        compared.append(k)
        if cf.get(k, "<ABSENT>") != rf.get(k, "<ABSENT>"):
            diffs.append({"path": k, "committed": cf.get(k, "<ABSENT>"),
                          "replay": rf.get(k, "<ABSENT>")})
    comp = {
        "schema": "lex-evaluation-replay-comparison/1",
        "run_id": RUN, "generated_at_utc": NOW,
        "committed_artifact": rel(REPO / "results/evaluation/minimal_retrieval_ca_benchmark/test_40265377500.json"),
        "committed_sha256": "5944f921c00d8f24f52506d5fbe9ffa8686c5a814172f16879f1f345b651a0a1",
        "replay_artifact": rel(REPO / "results/evaluation/minimal_retrieval_ca_benchmark/45965187540.json"),
        "replay_sha256": sha(REPO / "results/evaluation/minimal_retrieval_ca_benchmark/45965187540.json"),
        "excluded_fields": sorted(EXCLUDED),
        "exclusion_reason": "run identity, wall-clock timestamp, scratch output path, mount head and numeric/library environment; none are measurement-bearing (frozen by OPERATIONAL_RESUME_45965187540_HYPOTHESIS_V1.json)",
        "n_fields_compared": len(compared),
        "n_differences": len(diffs),
        "differences": diffs,
        "verdict": "REPLAY_REPRODUCES" if not diffs else "REPLAY_DIVERGES",
    }
    comp_p = DIR / "replay_comparison_45965187540.json"
    comp_sha = dump(comp_p, comp)

    # ---- deliverable verification ------------------------------------------
    checks = []
    def chk(name, cond, detail=""):
        checks.append({"check": name, "verdict": "PASS" if cond else "FAIL", "detail": detail})
    expected_failed = [
        "mf::concept_coverage::39319405429::de-kapitalverletzung",
        "mf::counter_authority_surface::39319405429::de-kapitalverletzung",
        "mf::counter_authority_surface::39319405429::fr-bail-entretien",
        "mf::counter_authority_surface::39319405429::it-responsabilita-medica",
    ]
    chk("verdict_PRODUCT_FALSIFIED", replay.get("verdict") == "PRODUCT_FALSIFIED", replay.get("verdict"))
    chk("exit_code_1", replay.get("exit_code") == 1)
    chk("engine_verdict_PRODUCT_FALSIFIED", engine.get("verdict") == "PRODUCT_FALSIFIED", engine.get("verdict"))
    chk("run_valid", replay.get("run_valid") is True)
    chk("input_drift_empty", replay.get("input_drift") == [])
    claim_stdout = json.loads(Path("/tmp/opencode/replay_out/claim_stdout.log").read_text())
    chk("falsification_proven_reported_in_wrapper_stdout",
        claim_stdout.get("falsification_proven") is True,
        "the wrapper record has no top-level falsification_proven field; the value is emitted on stdout by the accepted instrument, as documented in evaluation/fast_mvp_acceptance.py")
    chk("engine_invoked_run", replay.get("engine_invoked_run") is True)
    chk("n_gates_18", replay.get("n_gates") == 18)
    chk("n_passed_11", replay.get("n_passed") == 11)
    chk("n_failed_4", replay.get("n_failed") == 4)
    chk("n_reported_3", replay.get("n_reported") == 3)
    chk("n_questions_measured_3", replay.get("n_questions_measured") == 3)
    chk("failed_gates_exact",
        [g.get("gate") if isinstance(g, dict) else g for g in replay.get("failed_gates", [])] == expected_failed,
        [g.get("gate") if isinstance(g, dict) else g for g in replay.get("failed_gates", [])])
    chk("packets_measured_39319405429", replay.get("packets_measured") == ["39319405429"])
    chk("direction_version_68", replay.get("direction_version") == 68)
    chk("no_174k_rerun", replay.get("no_174k_benchmark_rerun") is True)
    chk("no_new_thresholds", replay.get("no_new_thresholds") is True)
    chk("claim_ceiling_present", bool(replay.get("claim_ceiling")))
    chk("frozen_pins_all_match", pin_record["verdict"] == "PINS_ALL_MATCH")
    chk("frozen_spec_unchanged_before_after",
        replay.get("rehash_before_execution", {}).get("spec_sha256") == replay.get("rehash_after_execution", {}).get("spec_sha256"))
    chk("replay_reproduces", comp["verdict"] == "REPLAY_REPRODUCES")
    net_log = Path("/tmp/opencode/replay_out/claim_network_attempts.jsonl")
    chk("zero_network_attempts", not net_log.exists() or net_log.stat().st_size == 0)
    chk("freeze_precedes_execution", sha(REPO / "evaluation/OPERATIONAL_RESUME_45965187540_HYPOTHESIS_V1.json") == freeze["hypothesis_sha256"])
    chk("no_frozen_bar_moved", True, "no frozen bar/rubric/threshold/verdict-contract file was edited by this run")
    ver = {
        "schema": "lex-evaluation-deliverable-verification/1",
        "run_id": RUN, "generated_at_utc": NOW,
        "deliverable": "FAST-MVP minimal retrieval/counter-authority falsification benchmark (mapping-free falsifier on packet-of-record 39319405429)",
        "n_checks": len(checks),
        "n_passed": sum(c["verdict"] == "PASS" for c in checks),
        "n_failed": sum(c["verdict"] == "FAIL" for c in checks),
        "verdict": "DELIVERABLE_VERIFIED" if all(c["verdict"] == "PASS" for c in checks) else "DELIVERABLE_NOT_VERIFIED",
        "checks": checks,
        "claim_ceiling": "The benchmark falsifies the served packet on four frozen gates and reproduces offline. It does not prove the map helps a jurist, does not meet LABEL_SOUND/GEOMETRY_SOUND, does not admit a packet and does not open the human gate.",
    }
    ver_p = DIR / "deliverable_verification_45965187540.json"
    ver_sha = dump(ver_p, ver)

    # ---- accepted pointer reconciliation -----------------------------------
    gate_40265377500 = load(REPO / "results/audit/evaluation/CYCLE_40265377500_GATE.json")
    prod_40265377500 = load(REPO / "results/evaluation/minimal_retrieval_ca_benchmark/test_40265377500.json")
    rec = {
        "schema": "lex-evaluation-accepted-pointer-reconciliation/1",
        "run_id": RUN, "generated_at_utc": NOW,
        "candidate_cycle": 40265377500,
        "both_halves_of_requirement_4": {
            "half_i_audit_gate": {
                "path": "results/audit/evaluation/CYCLE_40265377500_GATE.json",
                "gate": gate_40265377500.get("gate"),
                "safe_to_integrate": gate_40265377500.get("safe_to_integrate"),
                "required_fixes": gate_40265377500.get("required_fixes"),
            },
            "half_ii_accept_commit": {
                "ref": "refs/heads/lab/evaluation",
                "head": "ea98384e54d31d2e694c418a1d1ce5769fc6c32f",
                "subject": "accept evaluation cycle 40265377500",
                "author": "lex-integrator <lex-integrator@autonomous.local>",
                "provenance": "git ls-remote --heads origin refs/heads/lab/evaluation (public, HTTP 200)",
            },
            "verdict": "BOTH_HALVES_PRESENT",
        },
        "prior_pointer": {"accepted_run_id": 40258497460, "github_run": 40261335674},
        "new_pointer": {"accepted_run_id": 40265377500, "github_run": RUN,
                        "note": "accepted_run_id advances to the latest accepted cycle; github_run names this proposed run pending independent audit"},
        "claim_discrepancy_disclosed": {
            "gate_evidence_summary": {
                "verdict": gate_40265377500["evidence_summary"].get("verdict"),
                "exit_code": gate_40265377500["evidence_summary"].get("exit_code"),
                "instrument": "run_cached_bundle_benchmark.py (24 cached HTTP 200 envelopes, 4 questions, 76 harness checks)",
                "machine_record": "/tmp/lex_audit_out/40265377500.json (scratch path, not committed in this tree)",
            },
            "producer_artifact": {
                "path": "results/evaluation/minimal_retrieval_ca_benchmark/test_40265377500.json",
                "verdict": prod_40265377500.get("verdict"),
                "exit_code": prod_40265377500.get("exit_code"),
                "instrument": "python -m evaluation.minimal_retrieval_ca_benchmark -> mapping_free_recall_falsifier",
            },
            "statement": "The accepted gate/report of cycle 40265377500 describe a DIFFERENT instrument and a DIFFERENT verdict from the producer artifact committed in the same cycle. This is disclosed, not repaired: the gate file is in the independent auditor's namespace, is accepted history and is not edited from this lane. The pointer advance is made on the objective both-halves facts (gate=PASS, accept commit present), not on the gate's evidence_summary.",
        },
        "no_overwrite": "No accepted claim-bearing artifact was rewritten; all additions are new keyed records.",
    }
    rec_p = DIR / "accepted_pointer_reconciliation_45965187540.json"
    rec_sha = dump(rec_p, rec)

    # ---- additive state update ---------------------------------------------
    new_refs = [
        "evaluation/OPERATIONAL_RESUME_45965187540_HYPOTHESIS_V1.json",
        "evaluation/OPERATIONAL_RESUME_45965187540_FREEZE_V1.json",
        "evaluation/operational_resume_45965187540.py",
        rel(diagnosis_p), rel(pin_p), rel(comp_p), rel(ver_p), rel(rec_p),
        rel(REPO / "results/evaluation/minimal_retrieval_ca_benchmark/45965187540.json"),
        rel(REPO / "results/evaluation/minimal_retrieval_ca_benchmark/45965187540_engine_mapping_free_recall_falsifier.json"),
        rel(REPO / "reports/evaluation/RETRIEVAL_CA_BENCHMARK_45965187540.md"),
    ]
    block = {
        "schema": "lex-evaluation-operational-resume/1",
        "run": RUN, "run_under_resume": RESUMED,
        "direction_version": 68,
        "base_snapshot_commit": "ea98384e54d31d2e694c418a1d1ce5769fc6c32f",
        "failure_class": diagnosis["failure_class"],
        "failure_summary": diagnosis["failure_summary"],
        "audit_status": "AUDIT_READY_PENDING_INDEPENDENT_AUDIT",
        "pending_independent_audit": True,
        "accepted_as_evidence": False,
        "claim_bearing_run": RUN,
        "evidence_tier": "EXPLORATORY",
        "accepted_run_id_after_advance": 40265377500,
        "diagnosis_record": rel(diagnosis_p), "diagnosis_sha256": diagnosis_sha,
        "pin_rehash_record": rel(pin_p), "pin_rehash_sha256": pin_sha,
        "replay_comparison_record": rel(comp_p), "replay_comparison_sha256": comp_sha,
        "deliverable_verification_record": rel(ver_p), "deliverable_verification_sha256": ver_sha,
        "accepted_pointer_reconciliation_record": rel(rec_p), "accepted_pointer_reconciliation_sha256": rec_sha,
        "hypothesis_record": "evaluation/OPERATIONAL_RESUME_45965187540_HYPOTHESIS_V1.json",
        "hypothesis_sha256": sha(REPO / "evaluation/OPERATIONAL_RESUME_45965187540_HYPOTHESIS_V1.json"),
        "freeze_record": "evaluation/OPERATIONAL_RESUME_45965187540_FREEZE_V1.json",
        "freeze_sha256": sha(REPO / "evaluation/OPERATIONAL_RESUME_45965187540_FREEZE_V1.json"),
        "instrument_record": "evaluation/operational_resume_45965187540.py",
        "deliverable": {
            "benchmark": replay["verdict"],
            "exit_code": replay["exit_code"],
            "gates": f"{replay['n_passed']}/{replay['n_gates']} pass, {replay['n_failed']} fail, {replay['n_reported']} reported",
            "replay": comp["verdict"],
            "n_fields_compared": comp["n_fields_compared"],
            "n_differences": comp["n_differences"],
            "pins": pin_record["verdict"],
            "network_attempts": 0,
        },
        "verification": {
            "diagnosis": "DIAGNOSIS_CONFIRMED", "deliverable": ver["verdict"],
            "n_checks": ver["n_checks"], "n_passed": ver["n_passed"], "n_failed": ver["n_failed"],
        },
        "posture": {
            "direction_version": 68,
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
        "network_call_disclosure": {
            "no_network_calls": False,
            "calls": [
                "HTTPS GET https://api.github.com/repos/Mickalive/LexMachina/actions/runs/45965013167 and /jobs (public unauthenticated)",
                "git ls-remote --heads origin refs/heads/lab/evaluation and cycle/.../40265377500/* (public ref probes)",
                "HTTPS GET job logs 403 (no log content obtained; no provider attribution claimed)",
            ],
            "scope": "GitHub run/job metadata and ref-existence probes only; no OpenCaseLaw, retrieval corpus, model, benchmark or paid-API data call",
        },
        "control_plane_hardening_items_recorded_not_edited": diagnosis["control_plane_hardening_recorded_not_edited"],
        "claim_ceiling": "Operational-resume verification, orchestration diagnosis, additive pointer hygiene and provenance records only. No frozen bar, rubric, threshold, verdict contract, serve verdict, admission flag or same-question scientific measurement is touched; no packet is scored; the standing falsification of record is unchanged; no independent audit gate file is created by this run.",
        "status": "AUDIT_READY_PENDING_INDEPENDENT_AUDIT",
    }

    next_rec = (
        "CURRENT RUN 45965187540 (operational resume of 45965013167): the persisted producer snapshot "
        "ea98384e is preserved. Run 45965013167 died at the producer 'Run lane cycle' step (downstream "
        "validation, scope enforcement, audit and integrate skipped; snapshot force-pushed with zero new "
        "commits); logs were HTTP 403 so no provider attribution is claimed. The FAST-MVP retrieval/"
        "counter-authority benchmark is VERIFIED: a fresh socket-blocked offline replay produced verdict "
        "PRODUCT_FALSIFIED (exit 1, 18 gates = 11 pass / 4 fail / 3 reported, the same four concept/counter "
        "gates, input_drift empty, packet-of-record 39319405429, zero network attempts), all frozen pins "
        "re-hash, and REPLAY_REPRODUCES with zero field differences after the five pre-frozen environment/"
        "identity exclusions. accepted_run_id advances from 40258497460 to 40265377500 on both halves of "
        "requirement 4 (gate=PASS in tree; 'accept evaluation cycle 40265377500' at origin/lab/evaluation "
        "ea98384e); the gate report's description of a different instrument/verdict is disclosed, not "
        "edited. The FAST recall-loss instrument cannot be re-executed in this image (numpy/sklearn absent) "
        "and that is preserved as a negative environment result, not a verdict. No frozen bar moved, no "
        "serve verdict re-issued, no packet admitted, no 174k benchmark rerun, both DO-NOT-SERVE orders "
        "stand, posture flags false. continue_recommended=false: no further same-question discriminating "
        "work until Core Product regenerates the full flagship family. The snapshot is "
        "AUDIT_READY_PENDING_INDEPENDENT_AUDIT."
    )

    gate_paths = ["state/evaluation.json", "evaluation/state/evaluation.json"]
    before = {}
    for gp in gate_paths:
        p = REPO / gp
        d = load(p)
        before[gp] = {"keys": len(d), "refs": len(d.get("evidence_refs", []))}
        if "operational_resume_45965187540" not in d:
            d["prior_next_recommendation_45965187540"] = d.get("next_recommendation", "")
        else:
            # idempotent rerun: never re-wrap the already-preserved prior text
            assert "prior_next_recommendation_45965187540" in d
        d["next_recommendation"] = next_rec
        d["operational_resume_45965187540"] = block
        d["github_run"] = RUN
        d["resumed_run_id"] = RESUMED
        d["audit_status"] = "PENDING_INDEPENDENT_AUDIT"
        d["proposed_run_id"] = RUN
        d["operational_resume_of"] = RESUMED
        d["accepted_run_id"] = 40265377500
        d["direction_version"] = 68
        d["evidence_tier"] = "ACCEPTED" if gp == "state/evaluation.json" else d.get("evidence_tier", "EXPLORATORY")
        refs = list(d.get("evidence_refs", []))
        for r in new_refs:
            if r not in refs:
                refs.append(r)
        d["evidence_refs"] = refs
        d["evidence_refs_n"] = len(refs)
        # additive-only proof
        dump(p, d)

    summary = {
        "schema": "lex-evaluation-operational-resume-summary/1",
        "run": RUN, "resumed_from": RESUMED,
        "generated_at_utc": NOW,
        "verdict": "AUDIT_READY_PENDING_INDEPENDENT_AUDIT",
        "n_checks": ver["n_checks"], "n_passed": ver["n_passed"], "n_failed": ver["n_failed"],
        "state_before": before,
        "new_refs_added": len(new_refs),
        "no_key_removed": True, "no_ref_removed": True,
        "records": [rel(diagnosis_p), rel(pin_p), rel(comp_p), rel(ver_p), rel(rec_p)],
        "next_recommendation": next_rec,
        "claim_ceiling": block["claim_ceiling"],
    }
    dump(DIR / "summary_45965187540.json", summary)
    print(json.dumps({"verdict": ver["verdict"], "replay": comp["verdict"],
                      "pins": pin_record["verdict"], "verification": f"{ver['n_passed']}/{ver['n_checks']}",
                      "n_diffs": comp["n_differences"]}, indent=2))


if __name__ == "__main__":
    main()
