#!/usr/bin/env python3
"""Operational resume of evaluation snapshot 44708758013 — run 44715273665.

Run 44708758013's PRODUCER work is preserved as-is: its own final gates are
AUDIT_READY (2026-11-20T09:43:58Z) and the snapshot commit 7de561aa was
persisted. What failed was the PRODUCER step itself at the END of the cycle:
step 6 'Run lane cycle' ran 09:13:25Z->09:58:30Z = 2705 s = the 2700 s
LEX_WORK_QUANTUM + ~5 s step setup, then exited rc-78
(``LEX_WORK_QUANTUM_EXPIRED seconds=2700 pid=2401`` /
``Process completed with exit code 78.``), so steps 7
('Validate active MVP producer state') and 9 ('Enforce lane write scope') were
SKIPPED, audit and integrate were skipped, no gate file and no /audit ref
exist, and the resilience job dispatched this run.

This instrument performs NO measurement and NO re-derivation of any frozen
benchmark. It:

  prestate      writes the producer-quantum diagnosis, verifies snapshot
                integrity and byte-identity of the persisted 44708758013 pack
                against pins frozen BEFORE execution, and inventories the three
                residuals the quantum kill left open (R1 regression record,
                R2 dangling nested-refs citation, R3 stale audit-index rows).
  battery       executes the reused multilingual/provenance/regression test
                files under the documented no-pytest shim, with the frozen
                success rule: the ONLY permitted failure is the disclosed
                pre-existing latent red in test_mount_provenance_gate.py.
  state-update  additive state edit of state/evaluation.json and its lane
                mirror (evidence_refs_n == len, github_run parity).
  final-gates   nested_evidence_refs_guard + state_integrity_gate + write-scope
                predicate + residual-closure checks, writes final_gates.json,
                then runs this run's self-test and writes the audit index LAST
                (so no index row can go stale by construction).

Reused from the prior instrument module (import, never re-executed):
gate_half_one / gate_half_two / verify_ordered_work and their frozen pins.
No falsifier, probe, retrieval benchmark or universal-174k benchmark runs.
Write scope: evaluation/, tests/evaluation/, results/evaluation/,
reports/evaluation/, state/evaluation.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation import operational_resume_44708758013 as PRIOR  # reuse-first
from evaluation import operational_resume_44700681660 as GITH  # gits/gits_raw helpers

RUN = "44715273665"
RESUMED = "44708758013"
SNAPSHOT_HEAD = "7de561aaadecdc08d92df8cb59a5a05077857834"
ACCEPTED_RUN = 40265377500
DIRECTION_VERSION = 68
OUT = ROOT / "results" / "evaluation" / f"operational_resume_{RUN}"
PRIOR_DIR = f"results/evaluation/operational_resume_{RESUMED}"
# All artifacts this run WRITES live in its own namespace; PRIOR_DIR is read-only.
MY_DIR = f"results/evaluation/operational_resume_{RUN}"

HYPOTHESIS = f"evaluation/OPERATIONAL_RESUME_{RUN}_HYPOTHESIS_V1.json"
FREEZE = f"evaluation/OPERATIONAL_RESUME_{RUN}_FREEZE_V1.json"
INSTRUMENT = f"evaluation/operational_resume_{RUN}.py"
REPORT = f"reports/evaluation/OPERATIONAL_RESUME_{RUN}.md"
TEST = f"tests/evaluation/test_operational_resume_{RUN}.py"
JOBS_CAPTURE = f"{MY_DIR}/run_{RESUMED}_jobs_rest_capture.json"
ANNOT_CAPTURE = f"{MY_DIR}/run_{RESUMED}_team_annotations.json"
DIAGNOSIS = f"{MY_DIR}/run_{RESUMED}_producer_quantum_diagnosis.json"
BYTE_IDENTITY = f"{MY_DIR}/{RESUMED}_pack_byte_identity_at_resume.json"
RESIDUALS = f"{MY_DIR}/{RESUMED}_residual_closure.json"
REGRESSION = f"{MY_DIR}/{RUN}_regression_guard.json"
SELFTEST = f"{MY_DIR}/{RUN}_selftest.json"
RESULT = f"{MY_DIR}/{RUN}.json"
STATE_INTEGRITY = f"{MY_DIR}/{RUN}_state_integrity.json"
WRITE_SCOPE = f"{MY_DIR}/{RUN}_write_scope.json"
NESTED = f"{MY_DIR}/{RUN}_nested_evidence_refs.json"
FINAL_GATES = f"{MY_DIR}/{RUN}_final_gates.json"
AUDIT_INDEX = f"{MY_DIR}/{RUN}_AUDIT_INDEX.json"
STATE_UPDATE_REC = f"{MY_DIR}/{RUN}_state_update.json"
LANE_SUITE = "results/evaluation/lane_suite/44715273665.json"

# ---------------------------------------------------------------------------
# Frozen pins for the persisted 44708758013 producer pack. Recorded at intake
# (before this run wrote anything) so a later edit of any prior file is visible.
# ---------------------------------------------------------------------------
PRIOR_PACK_PINS = {
    "evaluation/OPERATIONAL_RESUME_44708758013_HYPOTHESIS_V1.json":
        "fbcf5e59050d2b9362c9c5d18bc52a8947be6186da5ae0c4099cc03d284cbc01",
    "evaluation/OPERATIONAL_RESUME_44708758013_FREEZE_V1.json":
        "9dc91b1116c37ef059f38b112059f3ed8089eefabd91ebed65f6856a2f5e0d32",
    "evaluation/OPERATIONAL_RESUME_44708758013_FREEZE_V1_1_AMENDMENT.json":
        "da7a508a00056bc982eb2ea44205217c8302b84212f087fd8564b23f59bb8e61",
    "evaluation/operational_resume_44708758013.py":
        "12040363b1e65d601fa554012a1b68a54019a3ef7b688ad8b8c4a5b60bf782c2",
    f"{PRIOR_DIR}/44708758013.json":
        "f7a549828b468a2947654bee2b1e526188144bc2ac549deec23a9f1afafca9aa",
    f"{PRIOR_DIR}/44708758013_final_gates.json":
        "bb2e0ad67c1ca00225dbe1257bc2dac1b156a1eec59329e6052108c2323a8743",
    f"{PRIOR_DIR}/44708758013_state_integrity.json":
        "f912a9c28e132b2bf3b60491f89fc34362daf12b01637c87466891e50fcbc212",
    f"{PRIOR_DIR}/44708758013_write_scope.json":
        "737c18ec57ed98f8f3e0a83fc205fc1a73f6606f63d0f93a98e1157ed818d111",
    f"{PRIOR_DIR}/44708758013_AUDIT_INDEX.json":
        "dc710dd9f018962aae6eb280f102a897ee189d1eb23d8d170056f7f6ef8a52d2",
    f"{PRIOR_DIR}/44708758013_regression_guard.json":
        "db3ca7adf6e9244afc6be4e8c69aa2d2c40e26eabbad98686fa2047e1976a9ef",
    f"{PRIOR_DIR}/44708758013_regression_guard_attempt1_latent_red.json":
        "db3ca7adf6e9244afc6be4e8c69aa2d2c40e26eabbad98686fa2047e1976a9ef",
    f"{PRIOR_DIR}/44708758013_latent_red_disclosure.json":
        "179678a0795245e39524865486576ed86c9719ac64e507f8795320017549da02",
    f"{PRIOR_DIR}/44708758013_nested_evidence_refs_runidlabel_attempt1.json":
        "314970db4985467a4e51bbe76ba0c4d36b8ce72ea5efbf5fd3f823871ca37cea",
    f"{PRIOR_DIR}/44700681660_producer_pack_byte_identity.json":
        "2aa80f18a945d54bf6b341c9f890174e3add173d14c4258eea01a91e707b0d59",
    f"{PRIOR_DIR}/run_44700681660_audit_quantum_diagnosis.json":
        "eeda85696f1daeaaafc3206ec05e3043448bceb425b26a30b2d0784884ce0966",
    "reports/evaluation/OPERATIONAL_RESUME_44708758013.md":
        "6c5914ca9a04d09cded5a313591123474893171db3a9db0d833647eec8f13851",
    "tests/evaluation/test_operational_resume_44708758013.py":
        "ec658ba9a648df6d01487798155849d153e8270525b6e2cf352706b8f256b5c9",
    "results/evaluation/lane_suite/44708758013.json":
        "0f044a40a062e8b824e4535c4b04a01875218fc7140e20b91fb85d5e05ad6f7b",
}
# Absent at intake: the path prior final-gates R6 cites as its nested-refs record.
PRIOR_CANONICAL_NESTED_ABSENT_AT_INTAKE = f"{PRIOR_DIR}/44708758013_nested_evidence_refs.json"

PIN_FAST_MVP_INSTRUMENT = "fa5aa9a5bf1b865cd1e4b418432440fb9c9228afb4d7c47fa68a66f907263283"
PIN_RULES_LABEL = "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"
PIN_RULES_GEOMETRY = "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633"
PIN_BENCHMARK_RECORD = "fd25345b02da6658edbd5ed8722c69c9b3c7dbbc22e7856740cfdd421c5c4592"

# Reused test battery (multilingual + provenance + prior-run regression test).
# Frozen in FREEZE_V1 before execution. pytest is absent; the shim is used and
# its verdict is an upper bound, disclosed as always.
BATTERY = [
    f"tests/evaluation/test_operational_resume_{RESUMED}.py",
    "tests/evaluation/test_mount_provenance_gate.py",
    "tests/evaluation/test_stand_ready_multilingual_probe.py",
    "tests/evaluation/test_cross_lingual_alignment_v10.py",
    "tests/evaluation/test_nested_evidence_refs_guard.py",
]
INHERITED_LATENT_RED_CASE = (
    "test_mount_provenance_gate.py::"
    "test_check_provenance_on_the_committed_tree_does_not_re_derive")


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha(rel: str) -> str | None:
    p = ROOT / rel
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def write_json(rel: str, obj: dict) -> None:
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def load_json(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# failure diagnosis
# ---------------------------------------------------------------------------
def diagnose_producer_quantum() -> dict:
    jobs = load_json(JOBS_CAPTURE)
    annots = load_json(ANNOT_CAPTURE)
    team = next(j for j in jobs["jobs"] if j["name"] == "team")
    step6 = next(s for s in team["steps"] if s["name"] == "Run lane cycle")
    skipped = [s["name"] for s in team["steps"] if s["conclusion"] == "skipped"]
    messages = [a["message"] for a in annots["annotations"]]
    dur = (datetime.strptime(step6["completed_at"], "%Y-%m-%dT%H:%M:%SZ")
           - datetime.strptime(step6["started_at"], "%Y-%m-%dT%H:%M:%SZ")).total_seconds()
    prior_fg = load_json(f"{PRIOR_DIR}/44708758013_final_gates.json")
    snapshot_state = GITH.gits("show", f"{SNAPSHOT_HEAD}:state/evaluation.json")
    state_ok = ('"direction_version": 68' in snapshot_state
                and '"cycle_status": "COMPLETE"' in snapshot_state)
    jobs_status = {j["name"]: j["conclusion"] for j in jobs["jobs"]}
    return {
        "schema": "lex-evaluation-orchestration-failure-capture/1",
        "run_id": int(RESUMED),
        "captured_by_run": int(RUN),
        "repository": "Mickalive/LexMachina",
        "captured_at_utc": now(),
        "capture_method": ("unauthenticated public GitHub REST (run, jobs and "
                           "check-run annotations endpoints); log bodies remain "
                           "HTTP 403 and are never quoted"),
        "provenance_commands": [
            "GET https://api.github.com/repos/Mickalive/LexMachina/actions/runs/44708758013",
            "GET https://api.github.com/repos/Mickalive/LexMachina/actions/runs/44708758013/jobs",
            "GET https://api.github.com/repos/Mickalive/LexMachina/check-runs/136194847946/annotations",
        ],
        "capture_records": [JOBS_CAPTURE, ANNOT_CAPTURE],
        "run": jobs["run"],
        "jobs": jobs["jobs"],
        "annotation_messages": messages,
        "failing_step": step6,
        "failing_step_duration_s": int(dur),
        "quantum_s": 2700,
        "duration_minus_quantum_s": int(dur) - 2700,
        "rc78_annotation_confirmed": "Process completed with exit code 78." in messages,
        "quantum_annotation_confirmed": any(
            m.startswith("LEX_WORK_QUANTUM_EXPIRED seconds=2700") for m in messages),
        "skipped_steps": skipped,
        "state_validation_skipped": "Validate active MVP producer state" in skipped,
        "write_scope_skipped": "Enforce lane write scope" in skipped,
        "state_would_have_passed_step_7": state_ok,
        "audit_job": jobs_status.get("audit"),
        "integrate_job": jobs_status.get("integrate"),
        "resilience_job": jobs_status.get("resilience"),
        "gate_written": False,
        "gate_path_checked": f"results/audit/evaluation/CYCLE_{RESUMED}_GATE.json",
        "audit_ref_for_resumed_run": [],
        "producer_pack_written_before_kill": {
            "final_gates_generated_at_utc": prior_fg.get("generated_at_utc"),
            "final_gates_verdict": prior_fg.get("verdict"),
            "final_gates_passed": prior_fg.get("passed"),
            "regression_guard_generated_at_utc": load_json(
                f"{PRIOR_DIR}/44708758013_regression_guard.json").get("generated_at_utc"),
            "latent_red_disclosure_generated_at_utc": load_json(
                f"{PRIOR_DIR}/44708758013_latent_red_disclosure.json").get(
                    "generated_at_utc"),
            "quantum_expired_at_utc": "2026-11-20T09:58:25Z",
            "story": ("the pack reached AUDIT_READY at 09:43:58Z, the regression "
                      "battery ran at 09:45:03Z and the latent-red disclosure was "
                      "written at 09:56:00Z; the agent was hard-killed ~2 min later "
                      "at the 2700 s quantum, so the disclosure's planned 'final "
                      "record' step and the index refresh never ran"),
        },
        "failure_class": "ORCHESTRATION_PRODUCER_QUANTUM_EXPIRY_RC78",
        "ruled_out": {
            "rc67_zero_delta": ("LEXT_REQUIRE_DELTA is set for this lane but the "
                                "rc-67 guard only fires on rc-0 exits and requires an "
                                "empty porcelain; this run exited 78 with a populated "
                                "workspace, and the snapshot commit 7de561aa was "
                                "persisted with 22 files"),
            "validation_failure": ("step 7 was SKIPPED, not failed; the snapshot "
                                   "state it would have checked carries "
                                   "direction_version=68 and cycle_status=COMPLETE, "
                                   "so it would have passed"),
            "write_scope_failure": ("step 9 was SKIPPED, not failed; the persisted "
                                    "snapshot contains only lane-scoped paths"),
            "gate_revise_or_blocked": ("no independent audit ran for this run at all; "
                                       "no gate file exists to be REVISE/BLOCKED"),
            "product_defect": ("the killed work is operational provenance and test "
                               "hygiene for the evaluation lane, not product code"),
        },
        "disposition": ("The producer session of run 44708758013 hit the wrapper's "
                        "2700 s LEX_WORK_QUANTUM (rc-78) two minutes AFTER its own "
                        "final gates were AUDIT_READY, so the workflow skipped the "
                        "state-validation and write-scope steps, skipped audit and "
                        "integrate, persisted the snapshot 7de561aa and the "
                        "resilience job dispatched this operational resume. This is "
                        "orchestration budget exhaustion - not a producer failure of "
                        "substance, not a validation failure and not a verdict. This "
                        "run preserves the pack byte-for-byte and closes the three "
                        "residuals the hard kill left open."),
        "controls": {
            "no_frozen_bar_or_threshold_changed": True,
            "no_falsifier_probe_or_benchmark_rerun": True,
            "no_universal_174k_benchmark": True,
            "no_log_body_quoted": True,
        },
        "claim_ceiling": ("Public metadata capture plus committed-artifact timing "
                          "only. It proves job/step conclusions, durations and "
                          "annotation text, not the agent's internal state beyond "
                          "those annotations."),
    }


def verify_snapshot_integrity() -> dict:
    head = GITH.gits("rev-parse", "HEAD").strip()
    diff = [l for l in GITH.gits("diff", "--name-only", "HEAD").splitlines() if l]
    porcelain = [l for l in GITH.gits_raw("status", "--porcelain").splitlines() if l]
    untracked = [l[3:] for l in porcelain if l.startswith("??")]
    tracked_mods = [l[3:] for l in porcelain if not l.startswith("??")]
    return {
        "head": head,
        "expected_head": SNAPSHOT_HEAD,
        "head_matches_snapshot": head == SNAPSHOT_HEAD,
        "tracked_tree_diff_vs_head": diff,
        "tracked_tree_identical_to_snapshot": not diff,
        "prior_snapshot_subject": GITH.gits("log", "-1", "--format=%s", head).strip(),
        "untracked_lane_files_added_by_this_run": untracked,
        "tracked_files_modified_by_this_run": tracked_mods,
        "no_prior_tracked_file_modified_by_this_run": not tracked_mods,
        "passed": head == SNAPSHOT_HEAD and not diff and not tracked_mods,
    }


def verify_prior_pack() -> dict:
    rows = []
    for rel, pin in PRIOR_PACK_PINS.items():
        actual = sha(rel)
        rows.append({"path": rel, "pinned_sha256": pin, "actual_sha256": actual,
                     "matches_pin": actual == pin})
    absent = PRIOR_CANONICAL_NESTED_ABSENT_AT_INTAKE
    prior_index = load_json(f"{PRIOR_DIR}/44708758013_AUDIT_INDEX.json")
    stale = []
    for row in prior_index.get("artifacts", []):
        declared_exists = row.get("exists")
        declared_sha = row.get("sha256")
        actual = sha(row["path"])
        if declared_exists is False or declared_sha is None or (
                declared_sha and actual and declared_sha != actual):
            stale.append({"path": row["path"], "index_declared_exists": declared_exists,
                          "index_declared_sha256": declared_sha,
                          "actual_sha256_at_resume": actual,
                          "actual_exists_at_resume": actual is not None})
    rec = {
        "schema": "lex-evaluation-prior-pack-byte-identity-at-resume/1",
        "run_id": int(RUN),
        "verified_run": int(RESUMED),
        "snapshot_head": SNAPSHOT_HEAD,
        "generated_at_utc": now(),
        "pins_frozen_before_execution": True,
        "n_files": len(rows),
        "all_match": all(r["matches_pin"] for r in rows),
        "prior_final_gates": {
            "record": f"{PRIOR_DIR}/44708758013_final_gates.json",
            "verdict": load_json(f"{PRIOR_DIR}/44708758013_final_gates.json").get("verdict"),
            "passed": load_json(f"{PRIOR_DIR}/44708758013_final_gates.json").get("passed"),
            "generated_at_utc": load_json(
                f"{PRIOR_DIR}/44708758013_final_gates.json").get("generated_at_utc"),
        },
        "canonical_nested_record_absent_at_intake": {
            "path": absent,
            "exists_now": (ROOT / absent).exists(),
            "why": ("prior phase_final_gates wrote the index and stamped the result "
                    "record afterwards, and the run-id-label amendment never got a "
                    "persisted corrected run; the run was quantum-killed first"),
        },
        "prior_index_stale_rows": stale,
        "prior_index_n_stale_rows": len(stale),
        "files": rows,
        "disposition": "PRESERVED_NOT_REWRITTEN - every file of run 44708758013 is "
                       "re-hashed, never modified; staleness is disclosed, not fixed "
                       "in place (F-3B convention).",
        "passed": all(r["matches_pin"] for r in rows),
    }
    write_json(BYTE_IDENTITY, rec)
    return rec


def close_residuals(pack: dict) -> dict:
    """R1/R2/R3 inventory + what this run does about each."""
    prior_reg = load_json(f"{PRIOR_DIR}/44708758013_regression_guard.json")
    prior_attempt = load_json(
        f"{PRIOR_DIR}/44708758013_regression_guard_attempt1_latent_red.json")
    disclosure = load_json(f"{PRIOR_DIR}/44708758013_latent_red_disclosure.json")
    rec = {
        "schema": "lex-evaluation-residual-closure/1",
        "run_id": int(RUN),
        "resumed_run": int(RESUMED),
        "generated_at_utc": now(),
        "R1_regression_record": {
            "prior_verdict": prior_reg.get("verdict"),
            "prior_n_failed": prior_reg.get("n_failed"),
            "prior_final_equals_attempt1": sha(
                f"{PRIOR_DIR}/44708758013_regression_guard.json") == sha(
                f"{PRIOR_DIR}/44708758013_regression_guard_attempt1_latent_red.json"),
            "disclosure": f"{PRIOR_DIR}/44708758013_latent_red_disclosure.json",
            "disclosure_classification": disclosure.get("classification"),
            "planned_but_never_executed": ("exclude the named latent-red case from the "
                                           "final regression record - the run was "
                                           "quantum-killed 2.5 min after the disclosure"),
            "this_runs_disposition": (
                "NOT excluded and NOT rewritten: this run re-executes the reused "
                "battery under its own run id with the frozen rule 'the only permitted "
                "failure is the disclosed inherited latent red', so the negative stays "
                "visible as evidence and the record is adjudicable."),
            "prior_files_preserved": True,
        },
        "R2_dangling_nested_citation": {
            "cited_by": f"{PRIOR_DIR}/44708758013_final_gates.json "
                        "-> rules.R6_nested_and_state.nested.record",
            "cited_path": PRIOR_CANONICAL_NESTED_ABSENT_AT_INTAKE,
            "exists": (ROOT / PRIOR_CANONICAL_NESTED_ABSENT_AT_INTAKE).exists(),
            "state_cites_it": False,
            "state_citation_checked": (
                PRIOR_CANONICAL_NESTED_ABSENT_AT_INTAKE
                in (ROOT / "state" / "evaluation.json").read_text(encoding="utf-8")),
            "root_cause": ("run-id-label defect (FREEZE_V1_1_AMENDMENT "
                           "RUN_ID_LABEL_DEFECT) plus the rc-78 kill before the "
                           "corrected run persisted"),
            "disposition": (
                "DISCLOSED_NOT_FABRICATED - a file named for run 44708758013 must "
                "hold 44708758013's own measurement, and no corrected record of that "
                "run exists on any ref; this run therefore does NOT author one. It "
                "re-executes the same guard under its own run id "
                f"({NESTED}) on the same state and publishes both paths."),
        },
        "R3_stale_audit_index": {
            "prior_index": f"{PRIOR_DIR}/44708758013_AUDIT_INDEX.json",
            "n_stale_rows": pack.get("prior_index_n_stale_rows"),
            "stale_rows": pack.get("prior_index_stale_rows"),
            "root_cause": ("write_audit_index() ran BEFORE phase_final_gates stamped "
                           "the result record, so the result sha went stale by "
                           "construction; the report and canonical nested rows were "
                           "written after the index; both are disclosed here"),
            "disposition": ("PRIOR INDEX NOT REWRITTEN. This run writes its own index "
                            "in the LAST step of its state-update phase, after every "
                            "referenced file exists and after the result record was "
                            "stamped, and asserts all_entries_exist before exit."),
        },
        "R4_no_independent_audit_gate": {
            "prior_gate_exists": (ROOT / f"results/audit/evaluation/CYCLE_{RESUMED}_GATE.json").exists(),
            "in_lane": False,
            "disposition": ("audit and integrate are workflow scope; this run makes "
                            "the snapshot adjudicable instead (fastest_verification_path)."),
        },
        "claim_ceiling": "Residual inventory and disposition only; no measurement.",
    }
    write_json(RESIDUALS, rec)
    return rec


def verify_freeze() -> dict:
    hyp, frz, inst = sha(HYPOTHESIS), sha(FREEZE), sha(INSTRUMENT)
    fz = load_json(FREEZE) if frz else {}
    checks = {
        "hypothesis_present": hyp is not None,
        "freeze_present": frz is not None,
        "instrument_present": inst is not None,
        "freeze_pins_hypothesis": fz.get("hypothesis_sha256") == hyp,
        "freeze_pins_instrument": fz.get("instrument_sha256") == inst,
        "direction_version_pinned": fz.get("direction_version") == DIRECTION_VERSION,
        "no_frozen_bar_edits": (
            sha("evaluation/frozen_bars/RULES_LABEL.json") == PIN_RULES_LABEL
            and sha("evaluation/frozen_bars/RULES_GEOMETRY.json") == PIN_RULES_GEOMETRY),
        "fast_mvp_instrument_unedited":
            sha("evaluation/fast_mvp_retrieval_recall_benchmark.py") == PIN_FAST_MVP_INSTRUMENT,
    }
    return {"passed": all(checks.values()), "checks": checks,
            "hypothesis_sha256": hyp, "freeze_sha256": frz, "instrument_sha256": inst}


def run_nested_guard(out_rel: str) -> dict:
    out_dir = (ROOT / out_rel).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    p = subprocess.run([sys.executable, "-m", "evaluation.nested_evidence_refs_guard",
                        "--run-id", RUN, "--out-dir", str(out_dir)],
                       cwd=ROOT, capture_output=True, text=True, timeout=300)
    rec_path = out_dir / f"{RUN}_nested_evidence_refs.json"
    rec = json.loads(rec_path.read_text(encoding="utf-8")) if rec_path.is_file() else {}
    return {"exit_0": p.returncode == 0, "verdict": rec.get("verdict"),
            "n_unresolved": rec.get("n_unresolved"),
            "n_top_level_unresolved": rec.get("n_top_level_unresolved"),
            "record": out_rel}


def run_state_gate(out_rel: str) -> dict:
    out = ROOT / out_rel
    out.parent.mkdir(parents=True, exist_ok=True)
    p = subprocess.run([sys.executable, "-m", "evaluation.state_integrity_gate",
                        "--run-id", RUN, "--out", str(out)],
                       cwd=ROOT, capture_output=True, text=True, timeout=180)
    rec = json.loads(out.read_text(encoding="utf-8")) if out.is_file() else {}
    return {"exit_0": p.returncode == 0, "verdict": rec.get("verdict"),
            "n_checks": rec.get("n_checks"), "n_passed": rec.get("n_passed"),
            "n_failed": rec.get("n_failed"), "record": out_rel}


def write_scope_snapshot() -> dict:
    status = GITH.gits_raw("status", "--porcelain", "-uall")
    entries, bad = [], []
    for line in status.splitlines():
        if len(line) < 4:
            continue
        p = line[3:]
        allowed = (p.startswith("evaluation/") or p.startswith("tests/evaluation/")
                   or p.startswith("results/evaluation/") or p.startswith("reports/evaluation/")
                   or p == "state/evaluation.json" or p.startswith("data/evaluation/")
                   or p.endswith(".pyc") or "__pycache__" in p)
        entries.append({"porcelain": line, "path": p, "allowed": allowed})
        if not allowed:
            bad.append(p)
    verdict = {"schema": "lex-evaluation-write-scope/1", "lane": "evaluation",
               "generated_at_utc": now(),
               "workflow_step": "Enforce lane write scope (core-lane.yml)",
               "n_entries": len(entries), "n_bad": len(bad), "bad_paths": bad,
               "verdict": "SCOPE_CLEAN" if not bad else "SCOPE_VIOLATION",
               "scope_clean": not bad, "entries": entries}
    write_json(WRITE_SCOPE, {"schema": "lex-evaluation-write-scope-envelope/1",
                             "mode": "live", "repo_root": str(ROOT),
                             "verdict": verdict})
    return {"exit_0": not bad, "verdict": verdict["verdict"],
            "n_entries": len(entries), "n_bad": len(bad), "record": WRITE_SCOPE}


def run_battery() -> dict:
    """Frozen multilingual/provenance battery under the no-pytest shim."""
    OUT.mkdir(parents=True, exist_ok=True)
    p = subprocess.run(
        [sys.executable, "evaluation/no_pytest_runner.py", "--run-id", RUN,
         "--repo-root", str(ROOT), "--out", str(ROOT / REGRESSION)]
        + [f"--test-file={t}" for t in BATTERY],
        cwd=ROOT, capture_output=True, text=True, timeout=900)
    rec = load_json(REGRESSION)
    failed_cases = []
    import_errors = []
    for r in rec.get("results", []):
        if r.get("status") == "IMPORT_ERROR":
            import_errors.append(r.get("test_file"))
        for c in r.get("cases", []):
            if c.get("status") == "FAIL":
                failed_cases.append(f"{Path(r['test_file']).name}::{c.get('test')}")
    only_inherited = failed_cases == [INHERITED_LATENT_RED_CASE]
    # FREEZE_V1_1 amendment: import-level environment errors are admitted ONLY
    # for the pre-declared file below (numpy is absent in this image; run
    # 40217938706 recorded the identical IMPORT_ERROR and still passed SHIM).
    # The file stays in the battery, executes 0 cases, and any other import
    # error or any extra failing case still fails the rule.
    known_env_import_errors = {
        "tests/evaluation/test_cross_lingual_alignment_v10.py":
            "No module named 'numpy'",
    }
    import_errors_ok = all(
        r.get("test_file") in known_env_import_errors
        and known_env_import_errors[r["test_file"]] in (r.get("error") or "")
        for r in rec.get("results", []) if r.get("status") == "IMPORT_ERROR")
    rule_pass = (only_inherited and rec.get("n_absent", 0) == 0
                 and import_errors_ok)
    rec["run_rule"] = {
        "frozen_rule": ("pass iff the ONLY failing case is the disclosed pre-existing "
                        "latent red in test_mount_provenance_gate.py and no test file "
                        "is absent"),
        "failed_cases": failed_cases,
        "only_inherited_latent_red": only_inherited,
        "inherited_latent_red_case": INHERITED_LATENT_RED_CASE,
        "root_cause_record": "results/evaluation/orchestration/39884405570_diagnosis.json",
        "root_cause_summary": ("V2 LATENT-RED since commit 8fe862e8 (evaluation cycle "
                               "39548140787) removed the state root block "
                               "'mapping_free_recall_falsifier'; n_do_not_re_derive=3 "
                               "!= len(PROVENANCE_SOURCES)=4"),
        "new_failures": [c for c in failed_cases if not c.endswith(
            INHERITED_LATENT_RED_CASE.split("::")[1])],
        "rule_pass": rule_pass,
        "import_errors": import_errors,
        "import_errors_rule": (
            "FREEZE_V1_1_AMENDMENT: import errors admitted only for the "
            "pre-declared numpy-absent file test_cross_lingual_alignment_v10.py "
            "(0 cases executed; identical IMPORT_ERROR recorded independently by "
            "run 40217938706 which passed SHIM); any other import error fails"),
        "excluded_from_record": [],
        "negative_result_preserved": True,
    }
    rec["shim_exit_code"] = p.returncode
    rec["shim_verdict_at_rule_level"] = "SHIM_RULE_PASS" if rule_pass else "SHIM_RULE_FAIL"
    write_json(REGRESSION, rec)
    return {"exit_0": p.returncode == 0, "rule_pass": rule_pass,
            "n_passed": rec.get("n_passed"), "n_failed": rec.get("n_failed"),
            "n_unsupported": rec.get("n_unsupported"), "n_absent": rec.get("n_absent"),
            "failed_cases": failed_cases, "record": REGRESSION}


def battery_summary() -> dict:
    """Reuse the frozen battery record written by --phase battery (no re-run)."""
    if (ROOT / REGRESSION).is_file() and "run_rule" in load_json(REGRESSION):
        rec = load_json(REGRESSION)
        rule = rec["run_rule"]
        return {"exit_0": rec.get("shim_exit_code", 1) in (0, 1),
                "rule_pass": rule["rule_pass"],
                "n_passed": rec.get("n_passed"), "n_failed": rec.get("n_failed"),
                "n_unsupported": rec.get("n_unsupported"),
                "n_absent": rec.get("n_absent"),
                "failed_cases": rule["failed_cases"], "record": REGRESSION,
                "reused_phase_record": True}
    return run_battery()


# ---------------------------------------------------------------------------
# phases
# ---------------------------------------------------------------------------
def phase_prestate() -> dict:
    freeze = verify_freeze()
    diag = diagnose_producer_quantum()
    snapshot = verify_snapshot_integrity()
    pack = verify_prior_pack()
    residuals = close_residuals(pack)
    ordered = PRIOR.verify_ordered_work()
    bench = sha("results/evaluation/fast_mvp_current_head_ca_falsifier/40105794124.json")
    ordered["item_3"]["sha256_matches_this_run_pin"] = bench == PIN_BENCHMARK_RECORD
    ordered["all_pins_match"] = bool(ordered.get("all_pins_match")
                                     and bench == PIN_BENCHMARK_RECORD)
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
        "resumes_snapshot_of_run": int(RESUMED),
        "snapshot_head": SNAPSHOT_HEAD,
        "accepted_run_id": ACCEPTED_RUN,
        "accepted_head_both_halves": {
            "half_i_audit_gate": GITH.gate_half_one(),
            "half_ii_accept_commit": GITH.gate_half_two(),
            "surfaces_read": "in-tree gate file + git object graph + origin/lab log",
        },
        "failure_diagnosis": {
            "classification": diag["failure_class"],
            "record": DIAGNOSIS,
            "producer_step_duration_s": diag["failing_step_duration_s"],
            "quantum_s": diag["quantum_s"],
            "rc78_annotation_confirmed": diag["rc78_annotation_confirmed"],
            "state_validation_skipped": diag["state_validation_skipped"],
            "write_scope_skipped": diag["write_scope_skipped"],
            "state_would_have_passed_step_7": diag["state_would_have_passed_step_7"],
            "gate_written": False,
            "producer_work_preserved": True,
            "ruled_out": diag["ruled_out"],
        },
        "snapshot_integrity": snapshot,
        "prior_pack_byte_identity": {
            "record": BYTE_IDENTITY, "n_files": pack["n_files"],
            "all_match": pack["all_match"],
            "prior_index_n_stale_rows": pack["prior_index_n_stale_rows"],
            "prior_verdict": pack["prior_final_gates"]["verdict"],
        },
        "residual_closure": {
            "record": RESIDUALS,
            "R1_regression": residuals["R1_regression_record"]["this_runs_disposition"],
            "R2_nested_citation": residuals["R2_dangling_nested_citation"]["disposition"],
            "R3_audit_index": residuals["R3_stale_audit_index"]["disposition"],
            "R4_audit_gate": residuals["R4_no_independent_audit_gate"]["disposition"],
        },
        "freeze_inputs": freeze,
        "ordered_work": ordered,
        "reuse": {
            "reused_prior_instrument_module": "evaluation/operational_resume_44708758013.py",
            "battery": BATTERY,
            "fast_mvp_benchmark": "re-hashed only; never re-executed",
            "falsifier_or_probe_rerun": False,
            "universal_174k_benchmark": False,
        },
        "verdict": ("SNAPSHOT_PACK_VERIFIED_PENDING_GATES"
                    if freeze["passed"] and snapshot["passed"] and pack["passed"]
                    and ordered["all_pins_match"] else "VERIFICATION_FAILED"),
        "claim_ceiling": (
            "Operational provenance: producer-quantum failure diagnosis, snapshot "
            "integrity, byte-identity of the persisted 44708758013 pack against "
            "pre-frozen pins, residual inventory, and read-only re-verification of "
            "the v68 ordered work. No quality measurement, no bar/rubric/threshold/"
            "gate-predicate/verdict-contract edit, no serve verdict, no packet "
            "admission, no human-gate claim, no universal-174k benchmark."),
        "posture": {"packet_admitted": False, "machine_gate_ready": False,
                    "human_gate_ready": False, "ready_for_owner_session": False,
                    "owner_decision_required": False, "continue_recommended": False},
    }
    write_json(RESULT, record)
    return record


STATE_REFS = [
    DIAGNOSIS, BYTE_IDENTITY, RESIDUALS, RESULT, JOBS_CAPTURE, ANNOT_CAPTURE,
    REGRESSION, REPORT, HYPOTHESIS, FREEZE, INSTRUMENT, TEST,
    FINAL_GATES, SELFTEST, NESTED, STATE_INTEGRITY, WRITE_SCOPE,
    LANE_SUITE,
    f"{PRIOR_DIR}/44708758013_final_gates.json",
    f"{PRIOR_DIR}/44708758013_latent_red_disclosure.json",
    f"{PRIOR_DIR}/44708758013_regression_guard_attempt1_latent_red.json",
    "reports/evaluation/OPERATIONAL_RESUME_44708758013.md",
    "results/evaluation/orchestration/39884405570_diagnosis.json",
    f"results/audit/evaluation/CYCLE_{ACCEPTED_RUN}_GATE.json",
    "results/evaluation/fast_mvp_current_head_ca_falsifier/40105794124.json",
    "evaluation/fast_mvp_retrieval_recall_benchmark.py",
    "evaluation/frozen_bars/RULES_LABEL.json",
    "evaluation/frozen_bars/RULES_GEOMETRY.json",
]


def phase_state_update() -> dict:
    """Additive state edit of both state files; parity fields kept identical."""
    added = [r for r in STATE_REFS if (ROOT / r).is_file()]
    missing = [r for r in STATE_REFS if not (ROOT / r).is_file()]
    block = {
        "schema": "lex-evaluation-operational-resume-state/1",
        "run": int(RUN),
        "claim_bearing_run": int(RUN),
        "resumes_snapshot_of": int(RESUMED),
        "snapshot_head": SNAPSHOT_HEAD,
        "direction_version": DIRECTION_VERSION,
        "mode": "OPERATIONAL_RESUME",
        "audit_status": "PENDING_INDEPENDENT_AUDIT",
        "pending_independent_audit": True,
        "accepted_as_evidence": False,
        "accepted_run_id_unchanged": ACCEPTED_RUN,
        "accepted_head_both_halves": {
            "gate": f"results/audit/evaluation/CYCLE_{ACCEPTED_RUN}_GATE.json gate=PASS "
                    "safe_to_integrate=true required_fixes=[]",
            "accept_commit": "origin/lab/evaluation ea98384e 'accept evaluation cycle "
                             f"{ACCEPTED_RUN}'",
            "surfaces_read": "in-tree gate file + git object graph + origin/lab log",
        },
        "failure_diagnosis": {
            "class": "ORCHESTRATION_PRODUCER_QUANTUM_EXPIRY_RC78",
            "record": DIAGNOSIS,
            "failing_step": "Run lane cycle (step 6)",
            "producer_step_duration_s": 2705,
            "quantum_s": 2700,
            "rc78_annotation_confirmed": True,
            "state_validation_skipped": True,
            "write_scope_skipped": True,
            "not_a_validation_failure": (
                "step 7 was skipped, not failed; the snapshot state carries "
                "direction_version=68 and cycle_status=COMPLETE and would have passed"),
            "no_gate_written": True,
            "producer_work_preserved": True,
        },
        "preservation": {
            "no_restart": True,
            "snapshot_commit": SNAPSHOT_HEAD,
            "prior_pack_byte_identity_record": BYTE_IDENTITY,
            "prior_pack_n_files": len(PRIOR_PACK_PINS),
            "prior_files_modified": False,
        },
        "residual_closure": {
            "record": RESIDUALS,
            "R1": "regression re-executed under this run's id with the frozen "
                  "'inherited-latent-red-only' rule; prior records preserved",
            "R2": "dangling canonical nested citation DISCLOSED_NOT_FABRICATED; "
                  "same guard re-executed under this run's id",
            "R3": "prior audit index NOT rewritten; this run's index is written last",
            "R4": "no audit gate exists for 44708758013; workflow scope, disclosed",
        },
        "result": RESULT,
        "report": REPORT,
        "final_gates": {"record": FINAL_GATES, "selftest": SELFTEST,
                        "nested_refs": NESTED, "state_integrity": STATE_INTEGRITY,
                        "write_scope": WRITE_SCOPE},
        "audit_index": (
            "written as the last artifact of this run inside the state-update "
            "phase; its path is deliberately not cited here because the nested "
            "guard scans every path-shaped string of this file and the index "
            "post-dates this write"),
        "freeze": {"hypothesis": HYPOTHESIS, "freeze": FREEZE,
                   "instrument": INSTRUMENT,
                   "direction_version_pinned": DIRECTION_VERSION,
                   "freeze_precedes_execution": True, "frozen_edits": []},
        "ordered_work_status": {
            "1": "DISCHARGED_ELSEWHERE_HASH_VERIFIED_NOT_RERUN (report b10eeb3a + "
                 "record 2e691dd0 re-hashed; no re-measure)",
            "2": "NOT_YET_DISCRIMINATING (frozen 15-member family 14/15; no full "
                 "protocol, no packet-of-record scoring)",
            "3": "KEPT_NOT_RERUN (benchmark of record 40105794124 fd25345b "
                 "PRODUCT_FALSIFIED on packet 39319405429)",
            "4": "REPORTED_ONLY_WHERE_QUOTED (not quoted this cycle)",
            "5": "HONOURED (no frozen bench / D2 / bypass re-derivation; no "
                 "universal-174k benchmark)",
        },
        "posture": {"packet_admitted": False, "machine_gate_ready": False,
                    "human_gate_ready": False, "ready_for_owner_session": False,
                    "owner_decision_required": False, "continue_recommended": False},
        "claim_ceiling": "Operational provenance and residual closure; no quality "
                         "measurement, no frozen edit, no serve verdict, no human-gate "
                         "claim, no universal-174k benchmark.",
    }
    out = {}
    for rel, label in (("state/evaluation.json", "root"),
                       ("evaluation/state/evaluation.json", "lane")):
        st = load_json(rel)
        prev_run = st.get("github_run")
        st["github_run"] = int(RUN)
        st["proposed_run_id"] = int(RUN)
        st["github_run_previous_44715273665"] = prev_run
        st[f"operational_resume_{RUN}"] = block
        refs = st.get("evidence_refs") or []
        add = [r for r in added if r not in refs]
        st["evidence_refs"] = refs + add
        st["evidence_refs_n"] = len(st["evidence_refs"])
        p = ROOT / rel
        p.write_text(json.dumps(st, indent=2, ensure_ascii=False) + "\n",
                     encoding="utf-8")
        out[label] = {"path": rel, "refs_added": len(add),
                      "evidence_refs_n": st["evidence_refs_n"],
                      "accepted_run_id": st["accepted_run_id"],
                      "direction_version": st["direction_version"],
                      "github_run": st["github_run"],
                      "cycle_status": st["cycle_status"]}
    rec = {"schema": "lex-evaluation-state-update/1", "run_id": int(RUN),
           "direction_version": DIRECTION_VERSION, "generated_at_utc": now(),
           "additive_only": True, "block_added": f"operational_resume_{RUN}",
           "accepted_run_id_unchanged": ACCEPTED_RUN,
           "refs_considered": len(STATE_REFS), "refs_added_files": len(added),
           "refs_missing_at_write_time": missing,
           "files": out,
           "parity_fields": ["accepted_run_id", "direction_version", "github_run"],
           "phase_order": ("prestate -> battery -> report -> final-gates -> "
                           "state-update -> post-state verification -> audit index "
                           "written last"),
           "note": ("the block cites every artifact that exists when the state is "
                    "written; the audit index and the post-state guard record post-"
                    "date this write and are therefore not cited inside the state "
                    "(the guard scans every path-shaped string of this file)")}
    # --- self-test (FREEZE_V1_2): runs HERE, after the state block exists and
    #     before the audit index is written, so the state assertions are real.
    st_proc = subprocess.run(
        [sys.executable, "evaluation/no_pytest_runner.py", "--run-id", RUN,
         "--repo-root", str(ROOT), "--out", str(ROOT / SELFTEST),
         f"--test-file={TEST}"],
        cwd=ROOT, capture_output=True, text=True, timeout=300)
    st_rec = load_json(SELFTEST) if (ROOT / SELFTEST).is_file() else {}
    st_ok = st_rec.get("n_failed") == 0 and st_proc.returncode == 0
    selftest_row = {"exit_0": st_ok, "n_passed": st_rec.get("n_passed"),
                    "n_failed": st_rec.get("n_failed"),
                    "n_unsupported": st_rec.get("n_unsupported"),
                    "record": SELFTEST,
                    "runs_after_state_exists": True,
                    "runs_before_audit_index": True}
    rec["selftest"] = selftest_row
    fg = load_json(FINAL_GATES)
    fg["selftest"] = selftest_row
    if not st_ok:
        fg["verdict"] = "SELFTEST_FAILED"
        fg["passed"] = False
        fg["exit_code"] = 1
    write_json(FINAL_GATES, fg)          # rewritten BEFORE the index hashes it
    result = load_json(RESULT)
    result["final_gates"] = {"verdict": fg["verdict"], "passed": fg["passed"],
                             "record": FINAL_GATES, "rule_pass": fg["rule_pass"]}
    result["selftest"] = selftest_row
    result["verdict"] = ("SNAPSHOT_AUDIT_READY" if fg["passed"] and st_ok
                         else "SELFTEST_FAILED")
    result["generated_at_utc"] = now()
    write_json(RESULT, result)           # stamped BEFORE the index hashes it
    # --- post-state verification: guard + state gate + write scope on the FINAL state
    nested2 = run_nested_guard(NESTED)
    integrity2 = run_state_gate(STATE_INTEGRITY)
    scope2 = write_scope_snapshot()
    rec["post_state_verification"] = {
        "nested_evidence_refs_guard": nested2,
        "state_integrity_gate": integrity2,
        "write_scope": scope2,
        "passed": bool(nested2["exit_0"] and nested2["n_unresolved"] == 0
                       and nested2["n_top_level_unresolved"] == 0
                       and integrity2["exit_0"] and integrity2["n_failed"] == 0
                       and integrity2["n_checks"] == 11 and scope2["n_bad"] == 0),
    }
    write_json(STATE_UPDATE_REC, rec)  # written BEFORE the index so its sha is stable
    # --- audit index written LAST, after every other artifact exists and the
    #     result record has been stamped (the prior run's staleness defect).
    final = load_json(FINAL_GATES)
    st_rec = load_json(SELFTEST) if (ROOT / SELFTEST).is_file() else {}
    selftest_row = final.get("selftest") or {
        "exit_0": st_rec.get("n_failed") == 0, "n_passed": st_rec.get("n_passed"),
        "n_failed": st_rec.get("n_failed"), "record": SELFTEST}
    write_audit_index(final, selftest_row)
    index = load_json(AUDIT_INDEX)
    return {**rec, "audit_index": {
        "record": AUDIT_INDEX, "written_last": True,
        "all_entries_exist": index["all_entries_exist"],
        "missing_entries": index["missing_entries"],
        "n_artifacts": len(index["artifacts"]), "sha256": sha(AUDIT_INDEX),
        "state_update_record_sha256": sha(STATE_UPDATE_REC)}}


def phase_final_gates() -> dict:
    battery = battery_summary()
    freeze = verify_freeze()
    snapshot = verify_snapshot_integrity()
    pack = load_json(BYTE_IDENTITY)
    residuals = load_json(RESIDUALS)
    nested = run_nested_guard(NESTED)
    integrity = run_state_gate(STATE_INTEGRITY)
    scope = write_scope_snapshot()
    rules = {
        "freeze_inputs": freeze,
        "snapshot_and_prior_pack": {
            "passed": bool(snapshot["passed"] and pack["passed"]),
            "snapshot_integrity": snapshot,
            "prior_pack": {"record": BYTE_IDENTITY, "all_match": pack["all_match"]},
        },
        "R5_regression_inherited_red_only": {
            "passed": bool(battery["rule_pass"]),
            "observed": battery,
        },
        "R6_nested_and_state": {
            "passed": bool(nested["exit_0"] and nested["n_unresolved"] == 0
                           and nested["n_top_level_unresolved"] == 0
                           and integrity["exit_0"] and integrity["n_failed"] == 0
                           and integrity["n_checks"] == 11),
            "nested": nested, "state_integrity": integrity,
        },
        "R7_write_scope": {"passed": bool(scope["exit_0"] and scope["n_bad"] == 0),
                           "observed": scope},
        "R8_residuals_disclosed": {
            "passed": bool(residuals["R2_dangling_nested_citation"]["exists"] is False
                           and residuals["R3_stale_audit_index"]["n_stale_rows"] >= 1
                           and residuals["R1_regression_record"]["prior_files_preserved"]),
            "observed": {"record": RESIDUALS,
                         "R1_preserved": residuals["R1_regression_record"][
                             "prior_files_preserved"],
                         "R2_exists": residuals["R2_dangling_nested_citation"]["exists"],
                         "R2_state_cites_it": residuals["R2_dangling_nested_citation"][
                             "state_cites_it"],
                         "R3_n_stale_rows": residuals["R3_stale_audit_index"][
                             "n_stale_rows"]},
        },
    }
    passed = all(r["passed"] for r in rules.values())
    final = {
        "schema": "lex-evaluation-operational-resume-final-gates/1",
        "run_id": int(RUN),
        "resumes_snapshot_of": int(RESUMED),
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
            "run 44708758013 reached AUDIT_READY at 09:43:58Z and then died at the "
            "2700 s producer quantum (rc-78) with three residuals open. This run "
            "preserves that pack byte-for-byte, re-executes the reused battery and "
            "the nested/state gates under its own id, discloses the dangling citation "
            "and stale index rows instead of rewriting them, and writes its audit "
            "index last so no row can go stale."),
        "claim_ceiling": "Operational provenance only; no quality measurement, no "
                         "frozen edit, no serve verdict, no human-gate claim, no "
                         "174k benchmark.",
    }
    write_json(FINAL_GATES, final)
    # FREEZE_V1_2: the self-test asserts this run's state block, which phase
    # state-update writes AFTER this phase. It therefore runs inside
    # state-update: after the state exists, before the audit index is written.
    selftest_row = {"status": "DEFERRED_TO_STATE_UPDATE_PHASE",
                    "record": SELFTEST, "runs_after_state_exists": True,
                    "runs_before_audit_index": True}
    # stamp the result record BEFORE the index is written (the prior run's bug)
    result = load_json(RESULT)
    result["final_gates"] = {"verdict": final["verdict"], "passed": passed,
                             "record": FINAL_GATES, "rule_pass": final["rule_pass"],
                             "nested": nested, "state_integrity": integrity,
                             "write_scope": scope}
    result["regression"] = {"record": REGRESSION, "rule_pass": battery["rule_pass"],
                            "n_passed": battery["n_passed"],
                            "n_failed": battery["n_failed"],
                            "failed_cases": battery["failed_cases"]}
    result["verdict"] = "SNAPSHOT_AUDIT_READY" if passed else "FINAL_GATES_FAILED"
    result["generated_at_utc"] = now()
    write_json(RESULT, result)
    final["selftest"] = selftest_row
    write_json(FINAL_GATES, final)
    # the audit index is written LAST, by phase state-update, after the state
    # files are updated and the post-state guard/state-gate runs complete.
    print(json.dumps({"phase": "final-gates", "verdict": final["verdict"],
                      "rule_pass": final["rule_pass"],
                      "audit_index_deferred_to": "phase state-update (written last)",
                      "selftest": {"status": selftest_row["status"],
                                   "record": SELFTEST}}, indent=1))
    return final


def write_audit_index(final: dict, selftest_row: dict) -> None:
    items = []
    for rel in [HYPOTHESIS, FREEZE,
                f"evaluation/OPERATIONAL_RESUME_{RUN}_FREEZE_V1_1_AMENDMENT.json",
                f"evaluation/OPERATIONAL_RESUME_{RUN}_FREEZE_V1_2_AMENDMENT.json",
                INSTRUMENT, REPORT, TEST, JOBS_CAPTURE, ANNOT_CAPTURE,
                DIAGNOSIS, BYTE_IDENTITY, RESIDUALS, RESULT, REGRESSION, SELFTEST,
                NESTED, STATE_INTEGRITY, WRITE_SCOPE, FINAL_GATES,
                STATE_UPDATE_REC, LANE_SUITE,
                f"{PRIOR_DIR}/44708758013_final_gates.json",
                f"{PRIOR_DIR}/44708758013_latent_red_disclosure.json",
                f"{PRIOR_DIR}/44708758013_regression_guard.json",
                f"results/audit/evaluation/CYCLE_{ACCEPTED_RUN}_GATE.json"]:
        items.append({"path": rel, "sha256": sha(rel), "exists": (ROOT / rel).is_file()})
    missing = [i["path"] for i in items if not i["exists"]]
    index = {
        "schema": "lex-evaluation-audit-index/1",
        "run_id": int(RUN),
        "resumes_snapshot_of": int(RESUMED),
        "generated_at_utc": now(),
        "written_as_the_last_artifact_of_the_run": True,
        "purpose": ("Pre-verified pack for the independent auditor: every "
                    "claim-bearing file of this run with its sha256, computed AFTER "
                    "the result record was stamped (the prior run's index went stale "
                    "because it was written before stamping)."),
        "headline": {
            "failure_class": "ORCHESTRATION_PRODUCER_QUANTUM_EXPIRY_RC78",
            "prior_pack_verdict": "AUDIT_READY (44708758013 final gates, passed=true, "
                                  "09:43:58Z) killed at the 2700 s quantum at 09:58:30Z",
            "this_run_verdict": final["verdict"],
            "prior_pack_byte_identity": load_json(BYTE_IDENTITY)["all_match"],
            "prior_index_stale_rows_disclosed": load_json(BYTE_IDENTITY)[
                "prior_index_n_stale_rows"],
            "ordered_work": "items 1-5 unchanged; no measurement rerun anywhere in this run",
        },
        "fastest_verification_path": [
            f"sha256 of the {len(PRIOR_PACK_PINS)} files pinned in {BYTE_IDENTITY}",
            f"python3 -m evaluation.state_integrity_gate --run-id {RUN} --out <tmp>",
            f"python3 -m evaluation.nested_evidence_refs_guard --run-id {RUN} --out-dir <tmp>",
            f"python3 evaluation/no_pytest_runner.py --run-id {RUN} "
            f"--test-file {TEST} --out <tmp>",
        ],
        "artifacts": items,
        "all_entries_exist": not missing,
        "missing_entries": missing,
        "claim_ceiling": "Operational provenance pack; no quality, serve or human-gate claim.",
    }
    write_json(AUDIT_INDEX, index)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--phase", choices=["prestate", "battery", "state-update",
                                        "final-gates"], required=True)
    args = ap.parse_args(argv)
    if args.phase == "prestate":
        rec = phase_prestate()
        print(json.dumps({"phase": "prestate", "verdict": rec["verdict"],
                          "pack_all_match": rec["prior_pack_byte_identity"]["all_match"]},
                         indent=1))
        return 0 if rec["verdict"] != "VERIFICATION_FAILED" else 1
    if args.phase == "battery":
        rec = run_battery()
        print(json.dumps({"phase": "battery", **rec}, indent=1))
        return 0 if rec["rule_pass"] else 1
    if args.phase == "state-update":
        rec = phase_state_update()
        ok = bool(rec["post_state_verification"]["passed"]
                  and rec["selftest"]["exit_0"]
                  and rec["audit_index"]["all_entries_exist"]
                  and not rec["audit_index"]["missing_entries"])
        print(json.dumps({"phase": "state-update", "files": rec["files"],
                          "refs_added_files": rec["refs_added_files"],
                          "post_state_verification": rec["post_state_verification"],
                          "audit_index": rec["audit_index"], "passed": ok}, indent=1))
        return 0 if ok else 1
    final = phase_final_gates()
    return final["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
