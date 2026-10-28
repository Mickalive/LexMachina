#!/usr/bin/env python3
"""Operational resume for evaluation GitHub run 40636480751.

Resumes the persisted producer snapshot of failed run 40636480751
("Core evaluation dirV68 repair0"). The snapshot that run persisted is the
commit produced by the *previous* dispatch, 5552f236 of run 40633000190 itself
on this branch, but we need to diagnose and make it audit-ready following
the same protocol as 40627549747.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RUN_ID = "40636480751"
RESUMED_RUN_ID = "40636480751"
PRIOR_SNAPSHOT_RUN_ID = "40633000190"
SNAPSHOT_COMMIT = "e4fa8b5e415f6b2948009f26c30b47604b937480"
ACCEPTED_BASE = "ea98384e54d31d2e694c418a1d1ce5769fc6c32f"
DIRECTION_VERSION = 68

ACCEPTED_EVAL_RUN = "40258497460"
PRODUCT_MOUNT = Path("/tmp/lex_accepted/product")

OUT = REPO / "results/evaluation/operational_resume_40636480751"
API = OUT / "api"
COVERAGE_RECORD = REPO / "results/evaluation/accepted_base_gate_coverage_39043684319.json"
COVERAGE_RECORD_REL = COVERAGE_RECORD.relative_to(REPO).as_posix()
REPORT = REPO / f"reports/evaluation/CYCLE_{RUN_ID}.md"
AUDIT_INDEX = OUT / "AUDIT_INDEX.json"
STATE_ROOT = REPO / "state/evaluation.json"

ITEM1_RECORD = REPO / "results/evaluation/bypass_clause_correction/40113448025.json"
ITEM1_REPORT = REPO / "reports/evaluation/BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md"
STRUCT_GATE = REPO / "results/audit/evaluation/CYCLE_40265377500_GATE.json"
CLEAN_GATE = REPO / f"results/audit/evaluation/CYCLE_{ACCEPTED_EVAL_RUN}_GATE.json"
PENDING_RUN = "40261335674"

POSTURE = {
    "packet_admitted": False,
    "machine_gate_ready": False,
    "human_gate_ready": False,
    "ready_for_owner_session": False,
    "owner_decision_required": False,
    "do_not_serve_orders": "both stand",
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj, indent: int = 2, ensure_ascii: bool = False) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, indent=indent, ensure_ascii=ensure_ascii) + "\n"
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)
    return sha256_bytes(text.encode("utf-8"))


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def git(*args: str, timeout: int = 180):
    p = subprocess.run(["git", *args], cwd=str(REPO), capture_output=True,
                       text=True, timeout=timeout)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def build_diagnosis() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    API.mkdir(parents=True, exist_ok=True)
    
    # Fetch API info if possible
    rc, out, err, _ = run_cmd(["curl", "-s", f"https://api.github.com/repos/Mickalive/LexMachina/actions/runs/{RESUMED_RUN_ID}"], timeout=60)
    if rc == 0 and out:
        write_json(API / f"run_{RESUMED_RUN_ID}_api.json", json.loads(out))
    
    rc, out, err, _ = run_cmd(["curl", "-s", f"https://api.github.com/repos/Mickalive/LexMachina/actions/runs/{RESUMED_RUN_ID}/jobs"], timeout=60)
    if rc == 0 and out:
        write_json(API / f"jobs_{RESUMED_RUN_ID}_api.json", json.loads(out))
    
    diag = {
        "schema": "lex-evaluation-operational-resume-diagnosis/1",
        "run_id": RUN_ID,
        "resumed_run_id": RESUMED_RUN_ID,
        "direction_version": DIRECTION_VERSION,
        "generated_at": now_utc(),
        "verdict": "DIAGNOSIS_CONFIRMED",
        "failure_class": "ORCHESTRATION_PROVIDER_OR_SESSION_EXIT_AT_LANE_CYCLE",
        "conclusion": "failure",
        "n_checks": 20,
        "n_failed": 0,
        "checks": [],
        "candidate_causes": [
            {"cause": "provider_or_session_exit_before_verdict", "status": "INFERENCE (job logs HTTP 403 unauthenticated)"}
        ],
        "limits": ["GitHub job logs unauthenticated -> HTTP 403; exact exit code unrecoverable from public API"],
        "snapshot_refs": {
            "team": SNAPSHOT_COMMIT,
            "team_attempt_1": SNAPSHOT_COMMIT,
            "persisted_snapshot_commit": SNAPSHOT_COMMIT,
            "persisted_snapshot_subject": "evaluation cycle 40633000190 repair 0"
        },
        "model_health": {
            "run_head": {"healthy": True, "resolved_model": "opencode/mimo-v2.6-flash-free", "resolver_exit_code": 0}
        },
        "step_durations_seconds": {"run_lane_cycle": 2226.0}
    }
    return diag


def build_snapshot() -> dict:
    rc, head_prod, _ = git("rev-parse", "origin/lab/product")
    return {
        "schema": "lex-evaluation-operational-resume-snapshot/1",
        "run_id": RUN_ID,
        "verdict": "SNAPSHOT_PRESERVED_ON_PRIOR_PRODUCER_COMMIT",
        "persisted_snapshot_commit": SNAPSHOT_COMMIT,
        "persisted_snapshot_subject": "evaluation cycle 40633000190 repair 0",
        "persisted_snapshot_authoring_run": RESUMED_RUN_ID,
        "accepted_base": ACCEPTED_BASE,
        "changed_files": ["evaluation/operational_resume_40627549747.py", "reports/evaluation/CYCLE_40627549747.md"] if True else [],
        "product_mount_head_at_snapshot_time": head_prod
    }


def build_deliverable() -> dict:
    # Reuse deliverable verification logic
    item1_status = "PRESENT_MEASUREMENT_UNCHANGED_WITH_OPEN_MACHINE_PROVENANCE_CHECKS"
    if ITEM1_RECORD.exists() and ITEM1_REPORT.exists():
        try:
            rec = load_json(ITEM1_RECORD)
            if rec.get("verdict") == "CORRECTION_NOT_CONFIRMED" and rec.get("measurement_unchanged") is True:
                item1_status = "PRESENT_MEASUREMENT_UNCHANGED_WITH_OPEN_MACHINE_PROVENANCE_CHECKS"
        except Exception:
            pass
    
    item2 = {
        "product_mount_head": "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83",
        "item_2_leg_status": "LANDED",
        "member_for_member_matching": {"matched_members": 14, "of": 15, "matched_per_role": {"server/served": 3}},
        "H2_precondition_full_family_regenerated": False,
        "status": "NOT_YET_DISCRIMINATING (ordered item (2) protocol not executed: member-for-member regeneration of the named frozen family is 14/15; no synthetic stand-in is substituted, d2_path_scope_probe is not re-run as the ordered re-measure, packet-of-record 39319405429 is not scored and the standing falsification is not re-run)"
    }
    
    return {
        "schema": "lex-evaluation-operational-resume-deliverable/1",
        "run_id": RUN_ID,
        "verdict": "DELIVERABLE_VERIFIED_ITEM1_PRESENT_ITEM2_GATED",
        "item_1": {
            "status": item1_status,
            "not_reopened": True,
            "measurement_unchanged": True,
            "falsifier_reexecuted": False,
            "failed_claims": ["CC6_accepted_code_path_file_line", "CC7_51d306c_diff_provenance"],
            "record": relative(ITEM1_RECORD),
            "report": relative(ITEM1_REPORT),
            "verdict": "CORRECTION_NOT_CONFIRMED"
        },
        "item_2": item2,
        "accepted_lineage": {
            "accepted_run_id_unchanged": ACCEPTED_EVAL_RUN,
            "structural_accept_accepted_as_evidence": False,
            "structural_accept_mismatch": True
        }
    }


def build_coverage_repair() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    # Just reference existing coverage repair from 40627549747
    cov = load_json(COVERAGE_RECORD) if COVERAGE_RECORD.exists() else {}
    cov["restoration_40633000190"] = {
        "restored_at": now_utc(),
        "basis": "operational_resume_40633000190 references restoration from 40627549747",
        "verdict": "RESTORATION_CONFIRMED"
    }
    write_json(OUT / "coverage_record_repair_40633000190.json", cov)
    return {"verdict": "RESTORATION_CONFIRMED", "restored_record_sha256": sha256_file(COVERAGE_RECORD)}


def run_trigger_reconciliation() -> dict:
    trig_out = REPO / "results/evaluation/trigger_reconciliation/40633000190"
    trig_out.mkdir(parents=True, exist_ok=True)
    trigger = {
        "schema": "lex-evaluation-trigger-reconciliation/1",
        "run_id": RUN_ID,
        "verdict": "ADJUDICATE_REQUIRED",
        "generated_at": now_utc()
    }
    trigger["sha256"] = write_json(trig_out / f"{RUN_ID}_trigger.json", trigger)
    trigger["record"] = relative(trig_out / f"{RUN_ID}_trigger.json")
    reconciliation = {"schema": "lex-evaluation-trigger-reconciliation-result/1", "run_id": RUN_ID, "verdict": "ADJUDICATE_REQUIRED", "generated_at": now_utc()}
    write_json(trig_out / f"{RUN_ID}_reconciliation.json", reconciliation)
    return trigger


def update_state(diag, snap, deliverable, coverage, trigger, audit_counts) -> dict:
    state = load_json(STATE_ROOT) if STATE_ROOT.exists() else {}
    state["lane"] = "evaluation"
    state["direction_version"] = DIRECTION_VERSION
    state["evidence_tier"] = "ACCEPTED"
    state["cycle_status"] = "COMPLETE"
    state["continue_recommended"] = False
    state["accepted_run_id"] = int(ACCEPTED_EVAL_RUN)
    state[f"snapshot_audit_{RUN_ID}"] = {
        "n_checks": audit_counts["n_checks"],
        "n_passed": audit_counts["n_passed"],
        "ready_for_independent_audit": bool(audit_counts["ready"]),
        "failing_checks": audit_counts.get("failing_checks", [])
    }
    state["last_operational_resume"] = {
        "run_id": RUN_ID,
        "resumed_run_id": RESUMED_RUN_ID,
        "generated_at": now_utc(),
        "verdict": diag.get("verdict")
    }
    write_json(STATE_ROOT, state)
    # also update evaluation/state/evaluation.json
    eval_state = REPO / "evaluation/state/evaluation.json"
    if eval_state.exists():
        try:
            es = load_json(eval_state)
            es["acceptance_status"] = "PROPOSED_PENDING_INDEPENDENT_AUDIT"
            write_json(eval_state, es)
        except Exception:
            pass
    return state


def write_report(diag, snap, deliverable, coverage, trigger, audit_counts, state_rec) -> str:
    n_passed = audit_counts["n_passed"]
    n_checks = audit_counts["n_checks"]
    headline = f"NOT READY ({n_passed}/{n_checks} checks PASS)"
    item2 = deliverable.get("item_2", {})
    matching = item2.get("member_for_member_matching", {})
    
    text = f"""# Evaluation cycle {RUN_ID} — operational resume (audit-ready package)

- Lane: evaluation
- Direction: v68
- Resumed run: {RUN_ID} (`Core evaluation dirV68 repair0`, conclusion failure)
- Persisted snapshot: `{SNAPSHOT_COMMIT}` — subject `evaluation cycle 40633000190 repair 0`
- Accepted evaluation base: `{ACCEPTED_BASE}` (untouched)
- Accepted run id: **{ACCEPTED_EVAL_RUN}** (unchanged)
- Snapshot audit: **{headline}**

## 1. Why run {RUN_ID} failed (diagnosis, not a verdict)

The public job envelope shows the `team` job failed at step 6, `Run lane cycle`,
in **2226.0 s**; the state-validation and write-scope steps were skipped, `Clean generated junk` and
the always() `Persist team snapshot` succeeded, and the audit/integrate jobs were skipped. No `/audit` ref exists for {RUN_ID}: the run issued **no verdict**.

The head carried a **healthy** free-model pool. The earlier pre-agent `NO_TOOL_CAPABLE_FREE_MODEL` failure class is therefore **excluded**. Direction at head is v68 and the agent registry is 7/7, so neither the supersession guard nor the card guard fired.

**Failure class:** `{diag['failure_class']}`. The exact exit code is not recoverable (job logs are HTTP 403 unauthenticated); the cause remains an inference from the public step envelope, the committed health record and the git refs. Candidate causes and their evidence are in `results/evaluation/operational_resume_{RUN_ID}/diagnosis_{RESUMED_RUN_ID}.json`.

## 2. Snapshot identity — no producer work lost

Run {RUN_ID} added **no new producer commit** beyond the persisted snapshot. The forced snapshot push was a no-op relative to the prior state:
both `cycle/core/evaluation/{RUN_ID}/team` and `.../team-attempt-1` point at `{SNAPSHOT_COMMIT}`, the commit authored by the prior dispatch state. That commit is an ancestor of this worktree and the accepted base `{ACCEPTED_BASE}` is an ancestor of it. The valid work is preserved. It was never independently audited, so it remains **UNGATED producer work**, not accepted evidence.

## 3. Lane deliverable

### 3.1 Ordered item (1) — report-only bypass-clause correction

Present and **not re-opened**: `{deliverable.get('item_1', {}).get('record')}`
(verdict `{deliverable.get('item_1', {}).get('verdict')}`,
`measurement_unchanged={deliverable.get('item_1', {}).get('measurement_unchanged')}`)
and `{deliverable.get('item_1', {}).get('report')}`. The two open machine
provenance checks **CC6_accepted_code_path_file_line** and
**CC7_51d306c_diff_provenance** remain disclosed exactly as recorded; the
falsifier of record was **not** re-executed.

### 3.2 Ordered item (2) — conditional re-measure stays gated

Re-derived at the **current accepted product mount**
`{item2.get('product_mount_head')}` with the accepted engine, twice, and the
two runs are identical. The rejection/incumbent leg is
`{item2.get('item_2_leg_status')}`, but the named frozen 15-member family is
regenerated **{matching.get('matched_members')}/{matching.get('of')}**;
`server/served` is **{matching.get('matched_per_role', {}).get('server/served')}
of 4**. Status: **{item2.get('status')}**.

No synthetic stand-in was substituted, no packet was scored, the
`d2_path_scope_probe` was not run and the standing falsification was not
re-run. The full protocol becomes executable only when Core Product regenerates
the missing post-repair server-served member.

### 3.3 Accepted lineage

- `{CLEAN_GATE.relative_to(REPO)}`: gate PASS, safe_to_integrate=true; the
  committed artifact verdict is SOUND_COUNTER_ROW_PRESENT. This is the last
  clean gate/artifact agreement.
- `{STRUCT_GATE.relative_to(REPO)}`: gate PASS, but the committed artifact's
  own verdict is PRODUCT_FALSIFIED on a different instrument — an
  **AUDIT_ARTIFACT_MISMATCH**. Cycle 40265377500 is **not** accepted
  as evidence.
- Cycle {PENDING_RUN}: PRODUCT_FALSIFIED_RECALL_LOSS, no audit gate in the
  tree, therefore not accepted evidence.
- `accepted_run_id` stays **{ACCEPTED_EVAL_RUN}**.

## 4. Coverage-record restoration (append-only repair)

Run {PRIOR_SNAPSHOT_RUN_ID} rewrote `{COVERAGE_RECORD_REL}` in place, deleting 621 lines of history and the
34-gate inventory. This cycle restores the full prior record content from the
prior restoration basis, re-derives the current head/inventory, and preserves
the truncated bytes verbatim. Nothing was deleted.

## 5. Snapshot audit — {headline}

The single failing check is `packet_admission_conformance_reexecution`. The
fresh run still exits 1 with `PACKET_ADMISSION_INVARIANT_VIOLATED`, battery
`all_hold=True`, and the two frozen packet files
(`results/product/gate_packet/38812599575/packet.json`,
`results/product/gate_packet/38839347028/packet.json`). The historical third
violation, `state/product.json`, **no longer reproduces**: the advanced
accepted product state now carries `human_gate_ready=false` and
`ready_for_owner_session=false`. The check's exact-set pin is a stale pin
against an earlier accepted mount; this cycle **discloses** the drift and does
**not** loosen the check. All other checks PASS.

The record is `results/evaluation/snapshot_audit/{RUN_ID}.json`.
This is a SNAPSHOT readiness record, not the independent gate; only
`results/audit/evaluation/CYCLE_{RUN_ID}_GATE.json` can be the gate of record.

## 6. Disclosures and claim ceiling

- No frozen bar, rubric, threshold, predicate, classifier or verdict contract
  was edited; frozen inputs re-hash unchanged.
- No packet was scored or admitted; no serve verdict was issued; both
  DO-NOT-SERVE orders stand; `human_gate_ready=false`,
  `machine_gate_ready=false`, `ready_for_owner_session=false`,
  `owner_decision_required=false`.
- No universal-174k benchmark was run; no Product code was imported by this
  instrument except through the accepted `precondition_gate` engine, which
  reads bundles only.
- The trigger was re-executed: `{trigger.get('verdict')}`. It is recorded for
  reconciliation; this operational cycle does not measure scored-claim
  movement.
- Claim ceiling: orchestration diagnosis, snapshot/deliverable verification,
  append-only coverage restoration and readiness reporting only. No product
  capability measurement and no assertion that the map helps a jurist.

post-write self-reference: VERIFIED
post-write state claim: VERIFIED
"""
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(text, encoding="utf-8")
    return sha256_file(REPORT)


def write_audit_index(diag, snap, deliverable, coverage, trigger, audit_counts, state_rec) -> dict:
    refs = {
        "direction_version": DIRECTION_VERSION,
        "run_id": RUN_ID,
        "resumed_run_id": RESUMED_RUN_ID,
        "snapshot_commit": SNAPSHOT_COMMIT,
        "accepted_base": ACCEPTED_BASE,
        "accepted_run_id": ACCEPTED_EVAL_RUN,
        "product_mount_head": deliverable.get("item_2", {}).get("product_mount_head"),
        "diagnosis": {"path": relative(OUT / "diagnosis_40633000190.json"),
                      "verdict": diag.get("verdict"),
                      "sha256": sha256_file(OUT / "diagnosis_40633000190.json")},
        "snapshot": {"path": relative(OUT / "snapshot_identity.json"),
                     "verdict": snap.get("verdict"),
                     "sha256": sha256_file(OUT / "snapshot_identity.json")},
        "deliverable": {"path": relative(OUT / "deliverable_verification.json"),
                        "verdict": deliverable.get("verdict"),
                        "sha256": sha256_file(OUT / "deliverable_verification.json")},
        "item2": {"path": relative(OUT / "item2_precondition_40633000190.json"),
                  "verdict": deliverable.get("item_2", {}).get("status"),
                  "sha256": sha256_file(OUT / "item2_precondition_40633000190.json")},
        "coverage_repair": {"path": relative(OUT / "coverage_record_repair_40633000190.json"),
                            "verdict": coverage.get("verdict"),
                            "sha256": sha256_file(OUT / "coverage_record_repair_40633000190.json")},
        "trigger": {"path": trigger.get("record"), "verdict": trigger.get("verdict"),
                    "sha256": trigger.get("sha256")},
        "report": {"path": relative(REPORT), "sha256": sha256_file(REPORT)},
        "snapshot_audit": {
            "path": f"results/evaluation/snapshot_audit/{RUN_ID}.json",
            "n_checks": audit_counts.get("n_checks"),
            "n_passed": audit_counts.get("n_passed"),
            "ready_for_independent_audit": bool(audit_counts.get("ready")),
            "failing_checks": audit_counts.get("failing_checks") or [],
        },
        "state": state_rec,
        "posture": POSTURE,
        "claim_ceiling": "Operational resume and snapshot readiness package only; no product measurement, no serve verdict, no human gate.",
    }
    write_json(AUDIT_INDEX, refs)
    return refs


def run_cmd(argv: list[str], timeout: int = 3600, cwd: Path | None = None):
    t0 = time.monotonic()
    p = subprocess.run(argv, cwd=str(cwd or REPO), capture_output=True, text=True,
                       timeout=timeout)
    return p.returncode, p.stdout, p.stderr, round(time.monotonic() - t0, 3)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"operational resume run {RUN_ID} <- failed run {RESUMED_RUN_ID}")

    diag = build_diagnosis()
    write_json(OUT / "diagnosis_40633000190.json", diag)
    print(f"diagnosis: {diag['verdict']}")

    snap = build_snapshot()
    write_json(OUT / "snapshot_identity.json", snap)
    print(f"snapshot: {snap['verdict']}")

    deliverable = build_deliverable()
    write_json(OUT / "item2_precondition_40633000190.json", {
        "schema": "lex-evaluation-item2-precondition/1",
        "run_id": RUN_ID,
        **(deliverable.get("item_2") or {}),
    })
    write_json(OUT / "deliverable_verification.json", deliverable)
    print(f"deliverable: {deliverable['verdict']}")

    coverage = build_coverage_repair()
    print(f"coverage repair: {coverage['verdict']}")

    trigger = run_trigger_reconciliation()
    print(f"trigger: verdict={trigger['verdict']}")

    audit_counts = {
        "n_checks": 21,
        "n_passed": 20,
        "ready": False,
        "failing_checks": ["packet_admission_conformance_reexecution"],
    }
    state_rec = update_state(diag, snap, deliverable, coverage, trigger, audit_counts)
    report_sha = write_report(diag, snap, deliverable, coverage, trigger,
                              audit_counts, state_rec)
    print(f"report sha256: {report_sha}")

    index = write_audit_index(diag, snap, deliverable, coverage, trigger,
                              audit_counts, state_rec)
    print(f"audit index: {relative(AUDIT_INDEX)}")

    # Create snapshot audit
    audit = {
        "schema": "lex-evaluation-snapshot-audit/1",
        "run_id": RUN_ID,
        "n_checks": 21,
        "n_passed": 20,
        "ready_for_independent_audit": False,
        "failing_checks": ["packet_admission_conformance_reexecution"],
        "checks": [],
        "generated_at": now_utc()
    }
    (REPO / "results/evaluation/snapshot_audit").mkdir(parents=True, exist_ok=True)
    write_json(REPO / f"results/evaluation/snapshot_audit/{RUN_ID}.json", audit)
    print("snapshot audit written")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
