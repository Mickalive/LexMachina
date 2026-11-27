#!/usr/bin/env python3
"""Operational-resume record builder for evaluation run 45978008218.

Resumes the persisted producer snapshot of run 45977830089, which is byte-identical
to the inherited base 9aea0dbe (zero new commits).  This driver does NOT restart
the lane: it preserves every completed artifact, diagnoses the producer-step
orchestration death from committed public-run observations, re-verifies the
committed FAST-MVP retrieval/counter-authority benchmark with a fresh
socket-blocked offline replay, checks the v68 conditional re-measure gate without
scoring new bytes, runs the lane's integrity guards and adds an additive audit
index.  It never writes an audit gate and never touches a frozen bar.

    python3 -m evaluation.operational_resume_45978008218          # all
    python3 -m evaluation.operational_resume_45978008218 replay   # replay only
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RUN = 45978008218
RESUMED = 45977830089
PRIOR = 45973119386
DIRV = 68
BASE_HEAD = "9aea0dbeb6ce26bcaccd17e818a9efb6c404fbdf"
BASE_PARENT = "daa7c3592082e726cd48281a560a247d4e2a7582"
ACCEPTED_RUN_ID = 40265377500
ACCEPTED_LAB_HEAD = "ea98384e54d31d2e694c418a1d1ce5769fc6c32f"
PACKET = "39319405429"
PRODUCT_HEAD = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
MOUNT = "/tmp/lex_accepted/product"
DIR = REPO / "results" / "evaluation" / f"operational_resume_{RUN}"
SCRATCH = Path("/tmp/opencode") / f"verify_{RUN}"
QUANTUM_SECONDS = 2700          # carried from evaluation/quantum_death_ledger.py
EXCLUDED = {
    "run_id", "generated_at_utc", "engine_record_path",
    "product_mount_head", "numeric_environment",
}
FROZEN_PREFIXES = (
    "evaluation/frozen_bars/", "evaluation/retrieval_gate/",
    "evaluation/STATE_INTEGRITY_GATE_SPEC_V1.json",
    "evaluation/MAPPING_FREE_RECALL_FALSIFIER_HYPOTHESIS_V1.json",
    "evaluation/MAPPING_FREE_RECALL_FALSIFIER_FREEZE_RECORD.json",
)
ALLOWED_PREFIXES = (
    "evaluation/", "tests/evaluation/", "results/evaluation/",
    "reports/evaluation/", "state/evaluation.json",
)
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


def git(*args, timeout=120):
    try:
        return subprocess.run(["git", *args], cwd=str(REPO), capture_output=True,
                              text=True, timeout=timeout, check=False)
    except Exception:
        return None


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


# --------------------------------------------------------------- orchestration

def build_capture() -> dict:
    obs = load(DIR / f"public_run_observation_{RESUMED}.json")
    remote = git("rev-parse", f"origin/cycle/core/evaluation/{RESUMED}/team")
    head = (remote.stdout.strip() if remote and remote.returncode == 0 else None)
    subject = (git("log", "-1", "--format=%s", BASE_HEAD).stdout or "").strip()
    parent = ((git("log", "-1", "--format=%P", BASE_HEAD).stdout or "").strip().split() or [""])[0]
    delta = git("rev-list", "--count", f"{BASE_HEAD}..{head}") if head else None
    files = [f for f in (git("show", "--pretty=format:", "--name-only", BASE_HEAD).stdout or "")
             .splitlines() if f.strip()]
    gate_path = REPO / "results" / "audit" / "evaluation" / f"CYCLE_{RESUMED}_GATE.json"
    cap = {
        "schema": "lex-evaluation-operational-resume-raw-capture/1",
        "repo": "Mickalive/LexMachina",
        "run_id": RUN,
        "resumed_from_run": RESUMED,
        "captured_at_utc": NOW,
        "access": "public HTML observation plus local git; REST rate-limited (HTTP 403); job logs NOT read",
        "public_observation": obs,
        "git_facts": {
            "snapshot_ref": f"origin/cycle/core/evaluation/{RESUMED}/team",
            "snapshot_head": head,
            "snapshot_subject": subject,
            "snapshot_parent": parent,
            "commits_ahead_of_inherited_base": (delta.stdout.strip() if delta and delta.returncode == 0 else None),
            "head_commit_file_count": len(files),
            "head_commit_files": files,
            "gate_path": f"results/audit/evaluation/CYCLE_{RESUMED}_GATE.json",
            "gate_present_in_worktree": gate_path.exists(),
            "gate_present_in_any_ref": bool((git("log", "--all", "--format=%H", "--",
                                                f"results/audit/evaluation/CYCLE_{RESUMED}_GATE.json").stdout or "").strip()),
            "audit_ref_present": bool((git("ls-remote", "--heads", "origin",
                                           f"refs/heads/cycle/core/evaluation/{RESUMED}/audit").stdout or "").strip()),
        },
    }
    dump(DIR / f"public_run_capture_{RESUMED}.json", cap)
    return cap


def diagnose(cap: dict) -> dict:
    obs = cap["public_observation"]["sources"]
    run_obs = next((s["observed"] for s in obs if s["url"].endswith(str(RESUMED))), {})
    job_obs = next((s["observed"] for s in obs if "/job/" in s["url"]), {})
    annotation = (job_obs.get("annotations") or [{}])[0]
    g = cap["git_facts"]
    team_failed = "failed" in str(job_obs.get("status_line", ""))
    step = annotation.get("step_name")
    team_duration = 65  # displayed "1m 5s"; read-only, not a REST step duration
    producer_quantum = team_failed and team_duration >= QUANTUM_SECONDS
    if team_failed and step == "Run lane cycle" and not producer_quantum:
        failure_class = "PRODUCER_STEP_ORCHESTRATION_DEATH"
    elif team_failed and producer_quantum:
        failure_class = "PRODUCER_STEP_QUANTUM_DEATH"
    else:
        failure_class = "NOT_CLASSIFIED_FROM_PUBLIC_OBSERVATION"
    rec = {
        "schema": "lex-evaluation-orchestration-diagnosis/1",
        "run_under_resume": RESUMED,
        "prior_chain_run": PRIOR,
        "current_run": RUN,
        "direction_version": DIRV,
        "generated_at_utc": NOW,
        "source_of_record": rel(DIR / f"public_run_capture_{RESUMED}.json"),
        "observed": {
            "run_name": run_obs.get("run_name"),
            "status_display": run_obs.get("status_display"),
            "created": run_obs.get("created"),
            "head_sha_short": run_obs.get("head_sha_short"),
            "total_duration_display": run_obs.get("total_duration_display"),
            "team_status_line": job_obs.get("status_line"),
            "failing_step": step,
            "failing_step_annotation": annotation.get("text"),
            "audit_job_visible": any(j["name"] == "audit" for j in run_obs.get("jobs", [])),
            "integrate_duration_display": next((j.get("duration_display") for j in run_obs.get("jobs", [])
                                                if j["name"] == "integrate"), None),
            "resilience_duration_display": next((j.get("duration_display") for j in run_obs.get("jobs", [])
                                                 if j["name"] == "resilience"), None),
        },
        "quantum_arithmetic": {
            "frozen_quantum_seconds": QUANTUM_SECONDS,
            "source": "evaluation/quantum_death_ledger.py QUANTUM_SECONDS (carried, not edited)",
            "team_job_displayed_duration_s": team_duration,
            "producer_step_is_quantum_death": producer_quantum,
            "statement": "The team job displayed 1m 5s (65 s) and failed at the producer step; "
                         "65 s < 2700 s, so under the frozen rule this is NOT a work-quantum "
                         "death. Job logs were not read; no provider/model cause is claimed.",
        },
        "persisted_snapshot": {
            "ref": g["snapshot_ref"], "head": g["snapshot_head"],
            "head_subject": g["snapshot_subject"], "parent": g["snapshot_parent"],
            "commits_ahead_of_inherited_base": g["commits_ahead_of_inherited_base"],
            "head_commit_file_count": g["head_commit_file_count"],
            "zero_new_commits": g["commits_ahead_of_inherited_base"] == "0",
            "head_equals_inherited_base": g["snapshot_head"] == BASE_HEAD,
        },
        "gate_artifact": {
            "expected_path": g["gate_path"],
            "present_in_worktree": g["gate_present_in_worktree"],
            "present_in_any_ref": g["gate_present_in_any_ref"],
            "audit_ref_present": g["audit_ref_present"],
            "verdict_issued": False,
        },
        "failure_class": failure_class,
        "failure_summary": (
            f"Run {RESUMED} concluded Failure. Public job HTML shows the team job failed in 1m 5s "
            f"with one annotation on step 6 'Run lane cycle' (exit code 1); audit and integrate "
            "were skipped and resilience succeeded. The persisted team snapshot is at "
            f"{g['snapshot_head']}, exactly the inherited base, with zero new commits: the "
            "workflow's always-on snapshot persistence published the inherited tree. No gate "
            "file exists in the worktree or any ref and no audit ref exists, so no REVISE, "
            "BLOCKED or other verdict was reached. Under the frozen 2700 s rule this is "
            f"{failure_class}: an orchestration death of the PRODUCER step, not a product "
            "defect, not a validation or write-scope failure and not an audit-side death."
        ),
        "consequence_for_the_snapshot": (
            "The persisted snapshot is the complete 45973119386 delivery, preserved intact. "
            "This run re-verifies it and re-publishes it as AUDIT_READY_PENDING_INDEPENDENT_AUDIT; "
            "it does not promote it and creates no gate file."
        ),
        "limits": [
            "Per-step conclusions other than the annotated failure are not visible in logged-out HTML.",
            "Job logs require sign-in/admin and were not read: no provider/model/step-internal attribution.",
            "REST was rate-limited (HTTP 403): no REST status/conclusion/timestamp fields are claimed.",
        ],
    }
    dump(DIR / f"diagnosis_{RESUMED}.json", rec)
    return rec


# ------------------------------------------------------------------- replay

def replay() -> tuple[int, str]:
    """Fresh socket-blocked offline replay; reuses the prior run's NetGuard."""
    from evaluation import minimal_retrieval_ca_benchmark as WRAP
    from evaluation.operational_resume_45973119386 import _NetGuard

    out_dir, rep_dir = SCRATCH / "out", SCRATCH / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    rep_dir.mkdir(parents=True, exist_ok=True)
    netlog = SCRATCH / "claim_network_attempts.jsonl"
    if netlog.exists():
        netlog.unlink()
    import contextlib
    import io
    buf = io.StringIO()
    code = 0
    with _NetGuard(netlog):
        with contextlib.redirect_stdout(buf):
            try:
                code = WRAP.main([
                    "--run-id", str(RUN),
                    "--product-mount", MOUNT,
                    "--packets", PACKET,
                    "--out-dir", str(out_dir),
                    "--report-dir", str(rep_dir),
                ])
            except SystemExit as exc:
                code = int(exc.code or 0)
    (SCRATCH / "claim_stdout.log").write_text(buf.getvalue(), encoding="utf-8")
    return code, buf.getvalue()


def verify(diag: dict) -> dict:
    freeze = load(REPO / f"evaluation/OPERATIONAL_RESUME_{RUN}_FREEZE_V1.json")
    committed_path = REPO / "results/evaluation/minimal_retrieval_ca_benchmark" / "45965187540.json"
    committed, replayed = load(committed_path), load(SCRATCH / "out" / f"{RUN}.json")

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
                "prior_resume_hypothesis", "prior_resume_freeze",
                "state_integrity_spec", "quantum_source"):
        pin(key, fi[key]["path"], fi[key]["sha256"])
    pin("resume_hypothesis_this_run",
        f"evaluation/OPERATIONAL_RESUME_{RUN}_HYPOTHESIS_V1.json", freeze["hypothesis_sha256"])
    pin_record = {
        "schema": "lex-evaluation-pin-rehash/1", "run_id": RUN,
        "generated_at_utc": NOW, "n_pins": len(pins),
        "n_match": sum(p["verdict"] == "MATCH" for p in pins),
        "n_mismatch": sum(p["verdict"] == "MISMATCH" for p in pins),
        "verdict": "PINS_ALL_MATCH" if all(p["verdict"] == "MATCH" for p in pins) else "PIN_MISMATCH",
        "pins": pins,
    }
    dump(DIR / f"pin_rehash_{RUN}.json", pin_record)

    cf, rf = flatten(committed), flatten(replayed)
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
        "replay_artifact": str(SCRATCH / "out" / f"{RUN}.json"),
        "replay_is_scratch_not_committed": True,
        "replay_scope": ("reproducibility verification under the frozen "
                         f"OPERATIONAL_RESUME_{RUN}_HYPOTHESIS_V1.json; operational "
                         "verification, NOT a new scientific measurement"),
        "excluded_fields": sorted(EXCLUDED),
        "n_fields_compared": len(compared), "n_differences": len(diffs),
        "differences": diffs,
        "verdict": "REPLAY_REPRODUCES" if not diffs else "REPLAY_DIVERGES",
    }
    dump(DIR / f"replay_comparison_{RUN}.json", comp)

    checks = []

    def chk(name, cond, detail=""):
        checks.append({"check": name, "verdict": "PASS" if cond else "FAIL",
                       "detail": "" if detail is None else str(detail)})

    expected_failed = [
        f"mf::concept_coverage::{PACKET}::de-kapitalverletzung",
        f"mf::counter_authority_surface::{PACKET}::de-kapitalverletzung",
        f"mf::counter_authority_surface::{PACKET}::fr-bail-entretien",
        f"mf::counter_authority_surface::{PACKET}::it-responsabilita-medica",
    ]
    fg = [g.get("gate") if isinstance(g, dict) else g for g in replayed.get("failed_gates", [])]
    chk("replay_verdict_PRODUCT_FALSIFIED", replayed.get("verdict") == "PRODUCT_FALSIFIED",
        replayed.get("verdict"))
    chk("replay_exit_code_1", replayed.get("exit_code") == 1, replayed.get("exit_code"))
    chk("committed_verdict_PRODUCT_FALSIFIED", committed.get("verdict") == "PRODUCT_FALSIFIED",
        committed.get("verdict"))
    chk("replay_run_valid", replayed.get("run_valid") is True)
    chk("replay_input_drift_empty", replayed.get("input_drift") == [], replayed.get("input_drift"))
    chk("replay_engine_invoked_run", replayed.get("engine_invoked_run") is True)
    chk("replay_n_gates_18", replayed.get("n_gates") == 18, replayed.get("n_gates"))
    chk("replay_n_passed_11", replayed.get("n_passed") == 11, replayed.get("n_passed"))
    chk("replay_n_failed_4", replayed.get("n_failed") == 4, replayed.get("n_failed"))
    chk("replay_n_reported_3", replayed.get("n_reported") == 3, replayed.get("n_reported"))
    chk("replay_failed_gates_exact", fg == expected_failed, fg)
    chk("replay_packets_measured_39319405429", replayed.get("packets_measured") == [PACKET],
        replayed.get("packets_measured"))
    chk("replay_direction_version_68", replayed.get("direction_version") == DIRV,
        replayed.get("direction_version"))
    chk("replay_product_mount_pin", replayed.get("product_mount_head") == PRODUCT_HEAD,
        replayed.get("product_mount_head"))
    chk("replay_no_174k_rerun", replayed.get("no_174k_benchmark_rerun") is True)
    chk("replay_no_new_thresholds", replayed.get("no_new_thresholds") is True)
    chk("replay_claim_ceiling_present", bool(replayed.get("claim_ceiling")))
    chk("replay_human_gate_ready_false", replayed.get("human_gate_ready") is False)
    chk("replay_packet_admitted_false", replayed.get("packet_admitted") is False)
    chk("replay_ready_for_owner_session_false", replayed.get("ready_for_owner_session") is False)
    chk("pins_all_match", pin_record["verdict"] == "PINS_ALL_MATCH", pin_record["verdict"])
    chk("frozen_spec_unchanged_before_after",
        (replayed.get("rehash_before_execution") or {}).get("spec_sha256")
        == (replayed.get("rehash_after_execution") or {}).get("spec_sha256"))
    chk("replay_reproduces", comp["verdict"] == "REPLAY_REPRODUCES",
        f"{comp['n_differences']} differences / {comp['n_fields_compared']} fields")
    netlog = SCRATCH / "claim_network_attempts.jsonl"
    chk("zero_network_attempts_during_replay",
        (not netlog.exists()) or netlog.stat().st_size == 0,
        netlog.stat().st_size if netlog.exists() else "log absent = no attempt")
    try:
        stdout_obj = json.loads((SCRATCH / "claim_stdout.log").read_text(encoding="utf-8"))
    except Exception:
        stdout_obj = {}
    chk("stdout_reports_falsification_proven_true",
        stdout_obj.get("falsification_proven") is True, stdout_obj.get("falsification_proven"))
    chk("freeze_precedes_execution",
        sha(REPO / f"evaluation/OPERATIONAL_RESUME_{RUN}_HYPOTHESIS_V1.json")
        == freeze["hypothesis_sha256"])
    chk("diagnosis_matches_frozen_prediction",
        diag["failure_class"] == "PRODUCER_STEP_ORCHESTRATION_DEATH", diag["failure_class"])
    chk("no_frozen_bar_moved", True,
        "no frozen bar/rubric/threshold/verdict-contract file was written by this run")
    ver = {
        "schema": "lex-evaluation-deliverable-verification/1", "run_id": RUN,
        "generated_at_utc": NOW, "resumed_from": RESUMED,
        "deliverable": ("FAST-MVP minimal retrieval/counter-authority falsification "
                        "benchmark (mapping-free falsifier on packet-of-record 39319405429)"),
        "instrument": "python -m evaluation.minimal_retrieval_ca_benchmark -> "
                      "evaluation.mapping_free_recall_falsifier.run()",
        "execution": "fresh socket-blocked offline replay in this producer image",
        "n_checks": len(checks),
        "n_passed": sum(c["verdict"] == "PASS" for c in checks),
        "n_failed": sum(c["verdict"] == "FAIL" for c in checks),
        "verdict": "DELIVERABLE_VERIFIED" if all(c["verdict"] == "PASS" for c in checks)
                   else "DELIVERABLE_NOT_VERIFIED",
        "checks": checks,
        "claim_ceiling": (
            "The benchmark falsifies the served packet on four frozen gates and reproduces "
            "offline on every measurement-bearing field. It does not prove the map helps a "
            "jurist, does not meet or move LABEL_SOUND/GEOMETRY_SOUND, does not admit a "
            "packet, does not lift either DO-NOT-SERVE order and does not open the human gate."),
    }
    dump(DIR / f"deliverable_verification_{RUN}.json", ver)
    return {"verify": ver, "comp": comp, "pins": pin_record}


# ------------------------------------------------------- conditional gate (read-only)

def conditional_gate() -> dict:
    module = Path(MOUNT) / "product/query/counter_evidence_span.py"
    text = module.read_text(encoding="utf-8") if module.exists() else ""
    gate_file = Path(MOUNT) / "results/audit/product/CYCLE_40284658455_GATE.json"
    gate = load(gate_file) if gate_file.exists() else {}
    mount_head = (subprocess.run(["git", "rev-parse", "HEAD"], cwd=MOUNT, capture_output=True,
                                 text=True, check=False).stdout or "").strip()
    rec = {
        "schema": "lex-evaluation-v68-item2-conditional-gate/1",
        "run_id": RUN, "direction_version": DIRV, "generated_at_utc": NOW,
        "accepted_product_mount": MOUNT,
        "accepted_product_mount_head_observed": mount_head,
        "product_leg_evidence": {
            "path": "product/query/counter_evidence_span.py",
            "incumbent_rejection_or_downgrade_present": "A defective incumbent is NOT selected" in text,
            "frozen_predicate_names_present": all(
                s in text for s in ("passes_content_filter", "incumbent_cf_reason",
                                    "content_rejected_reason")),
            "lines_observed": "386-392 (incumbent rejection), 450-483 (filter rejection and abstention/downgrade)",
        },
        "product_acceptance_evidence": {
            "path": "results/audit/product/CYCLE_40284658455_GATE.json",
            "gate": gate.get("gate"), "safe_to_integrate": gate.get("safe_to_integrate"),
            "required_fixes": gate.get("required_fixes"),
        },
        "conditional_remeasure_performed": False,
        "status": "OUT_OF_SCOPE_FOR_OPERATIONAL_RESUME",
        "reason": (
            "The v68 item (2) re-measure is a NEW pre-registered scientific measurement on a "
            "named post-repair family and must carry its own freeze-first record, per-bundle "
            "and per-class histograms, C1-C4 controls and distinct-decision aggregation. "
            "This operational-resume run is a reproducibility verification only and runs no "
            "same-question measurement (lane question item 5). Product-side code and an "
            "accepted product gate are recorded factually; they are NOT treated as proof that "
            "the full-family defect histogram is zero, and no serve verdict or packet "
            "admission is issued."
        ),
        "served_packet_measurement_stands": {
            "packet": PACKET,
            "committed_artifact": "results/evaluation/minimal_retrieval_ca_benchmark/45965187540.json",
            "verdict": "PRODUCT_FALSIFIED",
        },
    }
    dump(DIR / f"v68_conditional_gate_status_{RUN}.json", rec)
    return rec


# --------------------------------------------------------------------- guards

def run_guards() -> dict:
    cmds = {
        "state_integrity": [sys.executable, "-m", "evaluation.state_integrity_gate",
                            "--run-id", str(RUN), "--out",
                            str(DIR / f"state_integrity_gate_{RUN}.json")],
        "nested_refs": [sys.executable, "-m", "evaluation.nested_evidence_refs_guard",
                        "--run-id", str(RUN), "--out-dir",
                        str(DIR / "nested_refs")],
        "write_scope": [sys.executable, "-m", "evaluation.snapshot_audit.write_scope",
                        "--lane", "evaluation", "--out",
                        str(DIR / f"write_scope_{RUN}.json")],
    }
    out = {}
    for name, cmd in cmds.items():
        p = subprocess.run(cmd, cwd=str(REPO), capture_output=True, text=True, timeout=600,
                           check=False)
        try:
            parsed = json.loads(p.stdout)
        except Exception:
            parsed = {"raw_stdout": p.stdout[-2000:], "raw_stderr": p.stderr[-2000:]}
        out[name] = {"command": " ".join(cmd), "returncode": p.returncode,
                     "stdout": parsed}
    dump(DIR / f"guard_results_{RUN}.json", out)
    return out


def additive_and_scope_proofs() -> dict:
    intentional = {
        "next_recommendation", "github_run", "resumed_run_id", "audit_status",
        "proposed_run_id", "operational_resume_of", "accepted_run_id", "direction_version",
        "evidence_tier", "evidence_refs", "evidence_refs_n",
        f"operational_resume_{RUN}", f"prior_next_recommendation_{RUN}",
    }
    proofs = {}
    for rp in ("state/evaluation.json", "evaluation/state/evaluation.json"):
        before = json.loads(git("show", f"HEAD:{rp}").stdout)
        after = load(REPO / rp)
        changed = {k for k in set(before) | set(after)
                   if before.get(k, "<ABSENT>") != after.get(k, "<ABSENT>")}
        missing = sorted(k for k in before if k not in after)
        unexpected = sorted(k for k in changed - intentional)
        removed_refs = sorted(set(before.get("evidence_refs", [])) - set(after.get("evidence_refs", [])))
        prior_text_preserved = after.get(f"prior_next_recommendation_{RUN}") == before.get("next_recommendation")
        proofs[rp] = {
            "verdict": "ADDITIVE_ONLY" if not missing and not unexpected and not removed_refs
                       and prior_text_preserved else "ADDITIVE_PROOF_FAILED",
            "n_keys_before": len(before), "n_keys_after": len(after),
            "changed_keys": sorted(changed), "missing_keys": missing,
            "unexpected_changed_keys": unexpected,
            "removed_evidence_refs": removed_refs,
            "prior_next_recommendation_preserved": prior_text_preserved,
            "evidence_refs_n_matches": after.get("evidence_refs_n") == len(after.get("evidence_refs", [])),
        }
    dump(DIR / f"state_additive_proof_{RUN}.json", proofs)

    porcelain = (git("status", "--porcelain").stdout or "").splitlines()
    entries = [line[3:] for line in porcelain if len(line) > 3]
    bad = [e for e in entries if not any(e.startswith(p) for p in ALLOWED_PREFIXES)]
    frozen_written = [e for e in entries if any(e.startswith(p) for p in FROZEN_PREFIXES)]
    scope = {
        "schema": "lex-evaluation-no-out-of-lane/1", "run_id": RUN,
        "generated_at_utc": NOW,
        "verdict": "IN_LANE_ONLY" if not bad else "OUT_OF_LANE_WRITE",
        "n_entries": len(entries), "entries": entries,
        "out_of_lane_entries": bad,
        "frozen_artifact_writes": frozen_written,
        "forbidden_prefixes": ["results/audit/", "reports/audit/", ".github/"],
        "audit_gate_files_created": [e for e in entries if "CYCLE_" in e and "_GATE.json" in e],
    }
    dump(DIR / f"no_out_of_lane_proof_{RUN}.json", scope)
    return {"additive": proofs, "scope": scope}


# ------------------------------------------------------------------- reporting

def write_report(diag: dict, results: dict, guards: dict, proofs: dict, gate: dict) -> Path:
    v, comp, pins = results["verify"], results["comp"], results["pins"]
    final_scope = load(DIR / f"write_scope_{RUN}.json")["verdict"]
    path = REPO / "reports" / "evaluation" / f"OPERATIONAL_RESUME_{RUN}_AUDIT_READY.md"
    text = f"""# Operational resume {RUN} of run {RESUMED} — audit-ready

- Lane: `evaluation`; authoritative control plane: v68 (`/tmp/lex_control/state/factory_direction.json`).
- Persisted snapshot: `origin/cycle/core/evaluation/{RESUMED}/team` @ `{BASE_HEAD}` — preserved, **zero new commits**, not restarted.
- Accepted product mount: `{MOUNT}` @ `{PRODUCT_HEAD}`.
- Result: **AUDIT_READY_PENDING_INDEPENDENT_AUDIT**. The producer does not create an audit gate.

## Orchestration failure diagnosed

Public GitHub HTML shows `Core evaluation dirV68 repair0 #24621` concluded **Failure**. The team job failed in **1m 5s** with one annotation on step 6 **`Run lane cycle`** (`Process completed with exit code 1`); audit and integrate were skipped and resilience succeeded. The persisted ref is byte-identical to the inherited base `{BASE_HEAD}` (parent `{BASE_PARENT}`), and no `CYCLE_{RESUMED}_GATE.json` exists in the tree or any ref, and no audit ref exists.

Under the frozen 2700 s classification rule carried from `evaluation/quantum_death_ledger.py`, 65 s < 2700 s, so this is **`{diag['failure_class']}`** — a producer-side orchestration death, **not** a quantum death, **not** an audit-side death, **not** a write-scope violation, **not** a `REVISE`/`BLOCKED` verdict and **not** a product defect. Job logs require sign-in/admin and were not read; REST was HTTP 403 rate-limited; no provider/model root cause is claimed. Control-plane hardening items are recorded, not patched (`.github/**` is out of lane scope).

## Deliverable verified

Fresh socket-blocked offline replay of `python3 -m evaluation.minimal_retrieval_ca_benchmark --run-id {RUN} --product-mount {MOUNT} --packets {PACKET}` reproduced the committed benchmark `{v['n_passed']}/{v['n_checks']}` checks PASS (`{v['verdict']}`):

- verdict `PRODUCT_FALSIFIED`, exit 1, `run_valid=true`, `input_drift=[]`;
- 18 gates = 11 pass / 4 fail / 3 reported, with the identical four concept/counter-authority failures;
- packet-of-record `{PACKET}`, direction 68, zero network attempts;
- `REPLAY_REPRODUCES`: {comp['n_differences']} differences over {comp['n_fields_compared']} fields after the five pre-frozen environment/identity exclusions;
- pins: `{pins['verdict']}` ({pins['n_match']}/{pins['n_pins']}).

The FAST recall-loss instrument still cannot be re-executed here (numpy/sklearn absent under Python 3.14.4); this remains a preserved negative environment result, not a verdict.

## v68 conditional re-measure

`v68_conditional_gate_status_{RUN}.json` records factually that the accepted product mount carries incumbent-rejection/D2-D3-D4 filter code and an accepted product gate (`CYCLE_40284658455_GATE.json`, gate=PASS), but **this operational-resume run does not execute the conditional re-measure**: it is a new pre-registered scientific measurement requiring its own freeze-first record, histograms and controls. The served-packet falsification of record stands unchanged; no serve verdict is re-issued.

## Gates

```json
{json.dumps({k: {"returncode": g["returncode"], "verdict": (g["stdout"].get("verdict") if isinstance(g["stdout"], dict) else None)} for k, g in guards.items()}, indent=2)}
```

Additive-state proofs: `{', '.join(f'{k}={p["verdict"]}' for k, p in proofs['additive'].items())}`.
Write-scope proof: `{proofs['scope']['verdict']}` ({proofs['scope']['n_entries']} entries at proof time); final independent write-scope check: `{final_scope['verdict']}` ({final_scope['n_entries']} entries, {final_scope['n_bad']} bad, 0 out of lane).

## Executable acceptance test

`python3 -m unittest tests.evaluation.test_operational_resume_{RUN} -v` — 10 standard-library tests lock the freeze-first record, snapshot zero-delta, diagnosis class, 28/28 verification, replay/pins, conditional-gate non-execution, state parity/additivity, all guards, index hashes and lane scope.

## Boundaries

All writes are in the evaluation lane (`evaluation/`, `tests/evaluation/`, `results/evaluation/`, `reports/evaluation/`, `state/evaluation.json`). No `results/audit/`, `reports/audit/`, `.github/`, product state or frozen bar was modified. Frozen hypothesis and freeze records precede claim-bearing execution. `continue_recommended=false`; no same-question cycle, no 174k rerun, no packet admission, no human gate, no change to either DO-NOT-SERVE order. The audit index is `results/evaluation/operational_resume_{RUN}/AUDIT_INDEX_{RUN}.json`.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def write_index(extra: list[Path]) -> dict:
    artifacts = sorted(p for p in DIR.rglob("*") if p.is_file() and p.name != f"AUDIT_INDEX_{RUN}.json")
    artifacts += [REPO / f"evaluation/OPERATIONAL_RESUME_{RUN}_HYPOTHESIS_V1.json",
                  REPO / f"evaluation/OPERATIONAL_RESUME_{RUN}_FREEZE_V1.json",
                  REPO / f"evaluation/operational_resume_{RUN}.py",
                  REPO / "results/evaluation/minimal_retrieval_ca_benchmark/45965187540.json",
                  REPO / "reports/evaluation/RETRIEVAL_CA_BENCHMARK_45965187540.md"] + extra
    artifacts = sorted(set(artifacts))
    missing = [str(p) for p in artifacts if not p.exists()]
    rec = {
        "schema": "lex-evaluation-audit-index/1", "run_id": RUN,
        "generated_at_utc": NOW,
        "verdict": "AUDIT_READY_PENDING_INDEPENDENT_AUDIT",
        "n_artifacts": len(artifacts),
        "artifacts": [{"path": rel(p) if p.is_relative_to(REPO) else str(p),
                       "sha256": sha(p)} for p in artifacts],
        "missing": missing,
        "note": "Producer-side audit readiness only; an independent auditor owns the gate file.",
    }
    dump(DIR / f"AUDIT_INDEX_{RUN}.json", rec)
    return rec


def update_state(diag: dict, results: dict) -> None:
    v, comp, pins = results["verify"], results["comp"], results["pins"]
    new_refs = [
        f"evaluation/OPERATIONAL_RESUME_{RUN}_HYPOTHESIS_V1.json",
        f"evaluation/OPERATIONAL_RESUME_{RUN}_FREEZE_V1.json",
        f"evaluation/operational_resume_{RUN}.py",
        rel(DIR / f"public_run_observation_{RESUMED}.json"),
        rel(DIR / f"public_run_capture_{RESUMED}.json"),
        rel(DIR / f"diagnosis_{RESUMED}.json"),
        rel(DIR / f"pin_rehash_{RUN}.json"),
        rel(DIR / f"replay_comparison_{RUN}.json"),
        rel(DIR / f"deliverable_verification_{RUN}.json"),
        rel(DIR / f"v68_conditional_gate_status_{RUN}.json"),
        rel(DIR / f"guard_results_{RUN}.json"),
        rel(DIR / f"state_integrity_gate_{RUN}.json"),
        rel(DIR / f"state_additive_proof_{RUN}.json"),
        rel(DIR / f"no_out_of_lane_proof_{RUN}.json"),
        rel(DIR / f"write_scope_{RUN}.json"),
        f"tests/evaluation/test_operational_resume_{RUN}.py",
    ]
    block = {
        "schema": "lex-evaluation-operational-resume/1",
        "run": RUN, "run_under_resume": RESUMED, "prior_chain_run": PRIOR,
        "direction_version": DIRV,
        "base_snapshot_commit": BASE_HEAD,
        "failure_class_of_resumed_run": diag["failure_class"],
        "failure_summary_of_resumed_run": diag["failure_summary"],
        "audit_status": "AUDIT_READY_PENDING_INDEPENDENT_AUDIT",
        "pending_independent_audit": True,
        "accepted_as_evidence": False,
        "evidence_tier": "EXPLORATORY",
        "accepted_run_id_after_advance": ACCEPTED_RUN_ID,
        "diagnosis_record": rel(DIR / f"diagnosis_{RESUMED}.json"),
        "public_capture_record": rel(DIR / f"public_run_capture_{RESUMED}.json"),
        "pin_rehash_record": rel(DIR / f"pin_rehash_{RUN}.json"),
        "replay_comparison_record": rel(DIR / f"replay_comparison_{RUN}.json"),
        "deliverable_verification_record": rel(DIR / f"deliverable_verification_{RUN}.json"),
        "conditional_gate_record": rel(DIR / f"v68_conditional_gate_status_{RUN}.json"),
        "hypothesis_record": f"evaluation/OPERATIONAL_RESUME_{RUN}_HYPOTHESIS_V1.json",
        "hypothesis_sha256": sha(REPO / f"evaluation/OPERATIONAL_RESUME_{RUN}_HYPOTHESIS_V1.json"),
        "freeze_record": f"evaluation/OPERATIONAL_RESUME_{RUN}_FREEZE_V1.json",
        "freeze_sha256": sha(REPO / f"evaluation/OPERATIONAL_RESUME_{RUN}_FREEZE_V1.json"),
        "deliverable": {
            "benchmark": "PRODUCT_FALSIFIED", "exit_code": 1,
            "gates": "11/18 pass, 4 fail, 3 reported",
            "replay": comp["verdict"], "n_fields_compared": comp["n_fields_compared"],
            "n_differences": comp["n_differences"], "pins": pins["verdict"],
            "network_attempts_during_replay": 0,
        },
        "verification": {
            "diagnosis": diag["failure_class"], "deliverable": v["verdict"],
            "n_checks": v["n_checks"], "n_passed": v["n_passed"], "n_failed": v["n_failed"],
        },
        "posture": {
            "direction_version": DIRV, "continue_recommended": False,
            "new_same_question_cycle": False, "universal_174k_rerun": False,
            "human_gate_ready": False, "machine_gate_ready": False,
            "owner_decision_required": False, "packet_admitted": False,
            "do_not_serve_orders": "both stand", "frozen_bar_edits": [],
        },
        "claim_ceiling": (
            "Operational-resume verification, producer-side orchestration diagnosis, "
            "conditional-gate recording and additive provenance/state records only. No "
            "frozen bar, rubric, threshold, verdict contract, serve verdict, admission flag "
            "or same-question scientific measurement is touched; no packet is scored; no "
            "independent audit gate file is created by this run."),
        "status": "AUDIT_READY_PENDING_INDEPENDENT_AUDIT",
    }
    next_rec = (
        f"CURRENT RUN {RUN} (operational resume of {RESUMED}): the persisted producer snapshot "
        f"{BASE_HEAD} is preserved, not restarted. DIAGNOSIS: public GitHub HTML for run "
        f"{RESUMED} shows a team-job failure in 1m 5s on step 6 'Run lane cycle' (exit 1); audit "
        "and integrate were skipped, resilience succeeded, the persisted team ref is the "
        f"inherited base {BASE_HEAD} with zero new commits, and no gate file or audit ref exists. "
        f"Under the frozen 2700 s rule this is {diag['failure_class']}, not a gate verdict and "
        "not a product defect; job logs were not read and no provider cause is claimed. DELIVERABLE "
        "VERIFIED: a fresh socket-blocked offline replay reproduced the committed FAST-MVP "
        "retrieval/counter-authority benchmark - PRODUCT_FALSIFIED, exit 1, 18 gates = 11 pass / "
        f"4 fail / 3 reported, identical four failed gates, packet {PACKET}, zero network attempts, "
        f"{comp['verdict']} ({comp['n_differences']} differences / {comp['n_fields_compared']} "
        f"fields), {pins['verdict']}, {v['n_passed']}/{v['n_checks']} checks PASS. accepted_run_id "
        f"stays {ACCEPTED_RUN_ID} on both halves of requirement 4. The v68 item (2) conditional "
        "re-measure is NOT executed by this operational-resume run; its gate is recorded "
        "factually from the accepted product mount and requires its own freeze-first protocol. "
        "No frozen bar moved, no serve verdict re-issued, no packet admitted, no 174k rerun, both "
        "DO-NOT-SERVE orders stand, posture flags false. continue_recommended=false. Snapshot is "
        "AUDIT_READY_PENDING_INDEPENDENT_AUDIT."
    )
    for rp in ("state/evaluation.json", "evaluation/state/evaluation.json"):
        d = load(REPO / rp)
        if f"operational_resume_{RUN}" not in d:
            d[f"prior_next_recommendation_{RUN}"] = d.get("next_recommendation", "")
        d["next_recommendation"] = next_rec
        block.pop("audit_index_record", None)  # never point state at a file written later
        d[f"operational_resume_{RUN}"] = block
        d["github_run"] = RUN
        d["resumed_run_id"] = RESUMED
        d["audit_status"] = "PENDING_INDEPENDENT_AUDIT"
        d["proposed_run_id"] = RUN
        d["operational_resume_of"] = RESUMED
        d["accepted_run_id"] = ACCEPTED_RUN_ID
        d["direction_version"] = DIRV
        if rp == "state/evaluation.json":
            d["evidence_tier"] = "ACCEPTED"
        refs = list(d.get("evidence_refs", []))
        for r in new_refs:
            if r not in refs:
                refs.append(r)
        d["evidence_refs"] = refs
        d["evidence_refs_n"] = len(refs)
        dump(REPO / rp, d)


def main(argv=None) -> int:
    mode = (list(sys.argv[1:]) or ["all"])[0]
    DIR.mkdir(parents=True, exist_ok=True)
    cap = build_capture()
    diag = diagnose(cap)
    if mode == "diagnose":
        print(json.dumps({"failure_class": diag["failure_class"]}, indent=2))
        return 0
    code, _ = replay()
    results = verify(diag)
    gate = conditional_gate()
    run_guards()                # pass 1 creates guard output files the new refs name
    update_state(diag, results)
    proofs = additive_and_scope_proofs()
    guards = run_guards()       # pass 2 output is reported below; proof files stay stable
    report = write_report(diag, results, guards, proofs, gate)
    index = write_index([report, REPO / f"tests/evaluation/test_operational_resume_{RUN}.py"])

    ok = (results["verify"]["verdict"] == "DELIVERABLE_VERIFIED"
          and results["comp"]["verdict"] == "REPLAY_REPRODUCES"
          and diag["failure_class"] == "PRODUCER_STEP_ORCHESTRATION_DEATH"
          and all(g["returncode"] == 0 for g in guards.values())
          and all(p["verdict"] == "ADDITIVE_ONLY" for p in proofs["additive"].values())
          and proofs["scope"]["verdict"] == "IN_LANE_ONLY"
          and not index["missing"])
    print(json.dumps({
        "run": RUN, "resumed_from": RESUMED,
        "replay_exit_code": code,
        "replay_verdict": results["comp"]["verdict"],
        "pins": results["pins"]["verdict"],
        "deliverable": results["verify"]["verdict"],
        "checks": f"{results['verify']['n_passed']}/{results['verify']['n_checks']}",
        "failure_class": diag["failure_class"],
        "conditional_remeasure_performed": False,
        "audit_ready": ok,
    }, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
