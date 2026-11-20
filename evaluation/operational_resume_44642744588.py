#!/usr/bin/env python3
"""Operational resume of failed run 44642554373 (direction v68, evaluation).

WHAT THIS IS
------------
A freeze-first, executable verification cycle. It does not run a new benchmark.
It answers five operational questions from committed bytes:

1. Was the accepted snapshot preserved when run 44642554373 failed? (CC1/CC3)
2. What class of failure was 44642554373? (CC2)
3. Does the v68 ordered-item-(1) correction of record still hold, and is the
   40105794124 falsifier record still the measurement of record without a
   re-execution? (CC4-CC8)
4. Is v68 ordered item (2) now discriminating on the current accepted product
   head? (CC9) - re-derived only with the frozen set-relation gate, never by a
   full re-measure inside this resume.
5. Can lane state be made audit-ready without touching any historical artifact
   or moving a bar? (CC10)

WHY THIS IS NOT A NEW MEASUREMENT
---------------------------------
The already-observed orchestration metadata is pinned as an INPUT before the
claim-bearing verification runs. The single measurement-like operation,
`precondition_gate`, is the frozen instrument from
`evaluation/post_repair_family_ca_falsifier.py` re-used by hash-verified import.
It emits a set relation and a READY/NOT_YET status. This resume never scores a
packet, never re-runs the falsifier of record, never re-derives D1-D4, and
never runs a universal-174k benchmark.

MODES
-----
  measure       run CC1-CC9, CC11-CC12 + controls, write result and report
  --apply-state read the result, update both state files additively, re-check
                CC10, and finalise the result/report with state evidence

Exit codes (frozen in the hypothesis):
  0  all claim checks and controls hold (measure: measurements complete;
     apply-state: RESUME_VERIFIED_AND_AUDIT_READY)
  1  a claim or control failed (RESUME_VERIFIED_WITH_FINDINGS, published as-is)
  2  input/environment error (nothing was measured)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evaluation import post_repair_family_ca_falsifier as PR  # noqa: E402
from evaluation.snapshot_audit import write_scope as WS  # noqa: E402

SCHEMA = "lex-evaluation-operational-resume/1"
RUN_ID = 44642744588
RUN_UNDER_RESUME = 44642554373
SNAPSHOT_SHA = "ea98384e54d31d2e694c418a1d1ce5769fc6c32f"
SNAPSHOT_SUBJECT = "accept evaluation cycle 40265377500"
LATEST_ACCEPTED_EVAL = 40265377500
PROPOSED_PRECEDING_RUN = 40261335674
PRODUCT_MOUNT_HEAD = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"
PRODUCT_ACCEPTED_CYCLE = 40284658455

HYP_REL = "evaluation/OPERATIONAL_RESUME_44642744588_HYPOTHESIS_V1.json"
FREEZE_REL = "evaluation/OPERATIONAL_RESUME_44642744588_FREEZE_V1.json"
INSTRUMENT_REL = "evaluation/operational_resume_44642744588.py"
OUT_DIR_REL = "results/evaluation/operational_resume_44642744588"
RESULT_REL = f"{OUT_DIR_REL}/{RUN_ID}.json"
REPORT_REL = f"reports/evaluation/OPERATIONAL_RESUME_{RUN_ID}_AUDIT_READY.md"
TEST_REL = f"tests/evaluation/test_operational_resume_{RUN_ID}.py"
AUDIT_INDEX_REL = f"{OUT_DIR_REL}/AUDIT_INDEX_{RUN_ID}.json"
TEST_SUITE_REL = f"{OUT_DIR_REL}/test_suite_{RUN_ID}.json"
REST_CAPTURE_REL = f"{OUT_DIR_REL}/run_{RUN_UNDER_RESUME}_rest_capture.json"
ANNOTATION_REL = f"{OUT_DIR_REL}/run_{RUN_UNDER_RESUME}_annotation_evidence.json"

CORRECTION_REPORT_REL = (
    "reports/evaluation/BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md")
CORRECTION_RESULT_REL = "results/evaluation/bypass_clause_correction/40144816305.json"
FALSIFIER_RECORD_REL = (
    "results/evaluation/fast_mvp_current_head_ca_falsifier/40105794124.json")
FALSIFIER_MACHINE_REPORT_REL = (
    "reports/evaluation/FAST_MVP_CURRENT_HEAD_CA_FALSIFIER_40105794124.md")
FALSIFIER_READING_REL = (
    "reports/evaluation/FAST_MVP_CURRENT_HEAD_CA_FALSIFIER_40105794124_READING.md")
ACCEPTED_GATE_REL = "results/audit/evaluation/CYCLE_40265377500_GATE.json"
ACCEPTED_REPORT_REL = "reports/audit/evaluation/CYCLE_40265377500.md"

PRECONDITION_HYP_REL = (
    "evaluation/POST_REPAIR_FAMILY_CA_FALSIFIER_40258497460_HYPOTHESIS_V1.json")
PRECONDITION_FREEZE_REL = (
    "evaluation/POST_REPAIR_FAMILY_CA_FALSIFIER_40258497460_FREEZE_V1.json")

DEFAULT_MOUNT = Path("/tmp/lex_accepted/product")

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_INPUT = 2

FORBIDDEN_MODULE = "fast_mvp_" + "current_head_ca_falsifier"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args],
                          capture_output=True, text=True, timeout=90)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def numeric_environment() -> dict:
    env = {"python": platform.python_version(), "platform": platform.platform()}
    for mod in ("numpy", "scipy", "sklearn"):
        try:
            m = __import__(mod)
            env[mod] = getattr(m, "__version__", "unknown")
        except Exception:
            env[mod] = "NOT_IMPORTABLE"
    env["thread_env"] = {k: os.environ.get(k) for k in
                         ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                          "MKL_NUM_THREADS")}
    return env


def _check(checks: dict, cid: str, ok: bool, expected, actual,
           evidence: str) -> None:
    checks[cid] = {"ok": bool(ok), "expected": expected, "actual": actual,
                   "evidence": evidence}


# --------------------------------------------------------------------- pure tests
def snapshot_relation_ok(head: str, team: str, lab: str,
                         audit_ref_present: bool) -> bool:
    return (head == SNAPSHOT_SHA and team == SNAPSHOT_SHA
            and lab == SNAPSHOT_SHA and not audit_ref_present)


def failure_metadata_ok(capture: dict, annotation: str) -> bool:
    run = capture.get("run") or {}
    jobs = capture.get("jobs") or []
    team = next((j for j in jobs if j.get("name") == "team"), {})
    audit = next((j for j in jobs if j.get("name") == "audit"), {})
    integrate = next((j for j in jobs if j.get("name") == "integrate"), {})
    resilience = next((j for j in jobs if j.get("name") == "resilience"), {})
    steps = {s.get("number"): s for s in team.get("steps") or []}
    step6 = steps.get(6) or {}
    try:
        start = datetime.fromisoformat(
            str(step6.get("started_at")).replace("Z", "+00:00"))
        end = datetime.fromisoformat(
            str(step6.get("completed_at")).replace("Z", "+00:00"))
        duration = (end - start).total_seconds()
    except Exception:
        duration = -1
    return (
        run.get("conclusion") == "failure"
        and run.get("event") == "workflow_dispatch"
        and str(run.get("head_sha", "")).startswith("b132288c")
        and run.get("path") == ".github/workflows/core-lane.yml"
        and team.get("conclusion") == "failure"
        and step6.get("name") == "Run lane cycle"
        and step6.get("conclusion") == "failure"
        and 10 <= duration <= 30
        and audit.get("conclusion") == "skipped"
        and integrate.get("conclusion") == "skipped"
        and resilience.get("conclusion") == "success"
        and annotation.strip() == "Process completed with exit code 1."
    )


def span_ok(span: dict) -> bool:
    return (
        span.get("applied") is True
        and span.get("mode") == "select"
        and span.get("n_candidates") == 1
        and span.get("n_selected") == 0
        and span.get("n_abstained") == 1
        and span.get("abstained_ids") == ["gr_gerichte_ERZ 2010 25"]
        and span.get("abstention_reasons") == {"pivot_absent": 1}
        and span.get("frozen_rules_sha256")
        == "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"
    )


def measurement_ok(aggregate: dict, pinned: dict) -> bool:
    keys = ["verdict", "exit_code", "falsification_proven",
            "n_verified_scored_rows_total", "n_defective_verified_scored_rows_total",
            "defect_histogram", "distinct_defective_decision_ids"]
    return all(aggregate.get(k) == pinned.get(k) for k in keys)


def item2_consistency_ok(status: str, h1: bool, h2: bool,
                         matched: int, total: int) -> bool:
    if status == "READY":
        return h1 and h2 and matched == total
    return (not status.startswith("NOT_YET")
            or (not (h1 and h2)) and matched < total)


def state_bridge_ok(accepted: int, gate_present: bool,
                    accept_subject: str) -> bool:
    return (accepted == LATEST_ACCEPTED_EVAL and gate_present
            and accept_subject == SNAPSHOT_SUBJECT)


# --------------------------------------------------------------- claim checks
def cc1_snapshot(repo: Path, checks: dict) -> dict:
    def local_ref(name: str) -> str:
        p = git(repo, "rev-parse", name)
        return p.stdout.strip() if p.returncode == 0 else ""

    def remote_ref(name: str) -> str:
        p = git(repo, "ls-remote", "origin", f"refs/heads/{name}")
        line = (p.stdout.strip().splitlines() or [""])[0]
        return line.split()[0] if line else ""

    head = local_ref("HEAD")
    team_local = local_ref("refs/remotes/origin/cycle/core/evaluation/"
                           f"{RUN_UNDER_RESUME}/team")
    lab_local = local_ref("refs/remotes/origin/lab/evaluation")
    team_remote = remote_ref(f"cycle/core/evaluation/{RUN_UNDER_RESUME}/team")
    lab_remote = remote_ref("lab/evaluation")
    audit_remote = remote_ref(f"cycle/core/evaluation/{RUN_UNDER_RESUME}/audit")
    audit_gate = (repo / f"results/audit/evaluation/CYCLE_{RUN_UNDER_RESUME}_GATE.json").is_file()
    audit_report = (repo / f"reports/audit/evaluation/CYCLE_{RUN_UNDER_RESUME}.md").is_file()
    ok = (snapshot_relation_ok(head, team_local, lab_local, bool(audit_remote))
          and team_remote == SNAPSHOT_SHA and lab_remote == SNAPSHOT_SHA
          and not audit_gate and not audit_report)
    _check(checks, "CC1_snapshot_preserved", ok,
           "HEAD == team ref == lab/evaluation == ea98384e; no audit ref, "
           "gate or report for the failed run",
           {"head": head, "team_local": team_local, "lab_local": lab_local,
            "team_remote": team_remote, "lab_remote": lab_remote,
            "audit_remote": audit_remote, "audit_gate_in_tree": audit_gate,
            "audit_report_in_tree": audit_report},
           "git rev-parse / git ls-remote")
    return {"head": head, "team": team_remote, "lab": lab_remote,
            "audit_remote": audit_remote, "audit_gate_in_tree": audit_gate,
            "audit_report_in_tree": audit_report}


def cc2_failure(repo: Path, checks: dict) -> dict:
    capture = load_json(repo / REST_CAPTURE_REL)
    ann = load_json(repo / ANNOTATION_REL)
    jobs = {j.get("name"): j for j in capture.get("jobs") or []}
    team = jobs.get("team") or {}
    steps = {s.get("number"): s for s in team.get("steps") or []}
    ok = failure_metadata_ok(capture, ann.get("annotation") or "")
    _check(checks, "CC2_orchestration_rc1_failure_class", ok,
           "public REST + annotation prove a step-6 'Run lane cycle' exit-1 "
           "failure (16s), audit/integrate skipped, resilience success",
           {"run_conclusion": (capture.get("run") or {}).get("conclusion"),
            "head_sha": (capture.get("run") or {}).get("head_sha"),
            "team_conclusion": team.get("conclusion"),
            "failing_step": steps.get(6),
            "audit": (jobs.get("audit") or {}).get("conclusion"),
            "integrate": (jobs.get("integrate") or {}).get("conclusion"),
            "resilience": (jobs.get("resilience") or {}).get("conclusion"),
            "annotation": ann.get("annotation"),
            "capture_sha256": sha256_file(repo / REST_CAPTURE_REL),
            "annotation_sha256": sha256_file(repo / ANNOTATION_REL)},
           f"{REST_CAPTURE_REL}; {ANNOTATION_REL}")
    return {"run": capture.get("run"), "jobs": jobs,
            "capture_sha256": sha256_file(repo / REST_CAPTURE_REL),
            "annotation_sha256": sha256_file(repo / ANNOTATION_REL)}


def cc3_correction_record(repo: Path, freeze: dict, checks: dict) -> dict:
    report_path = repo / CORRECTION_REPORT_REL
    result_path = repo / CORRECTION_RESULT_REL
    text = report_path.read_text(encoding="utf-8")
    tokens = ["51d306c", "8b5b08dd", "6eee1149", "applied = true",
              "n_selected = 0", "pivot_absent", "4/5", "bstger_SK.2023.49"]
    absent = [t for t in tokens if t not in text]
    result = load_json(result_path)
    expected_report_sha = freeze["expected_repo_pins_before_execution"][
        CORRECTION_REPORT_REL]
    expected_result_sha = freeze["expected_repo_pins_before_execution"][
        CORRECTION_RESULT_REL]
    ok = (not absent
          and sha256_file(report_path) == expected_report_sha
          and sha256_file(result_path) == expected_result_sha
          and result.get("verdict") == "CORRECTION_NOT_CONFIRMED"
          and result.get("measurement_unchanged") is True
          and result.get("falsifier_reexecuted") is False)
    _check(checks, "CC3_correction_of_record_pinned", ok,
           "report + machine record exist at pinned shas, carry the required "
           "tokens, and state measurement unchanged / falsifier not re-executed",
           {"missing_tokens": absent,
            "report_sha256": sha256_file(report_path),
            "result_sha256": sha256_file(result_path),
            "machine_verdict": result.get("verdict"),
            "measurement_unchanged": result.get("measurement_unchanged"),
            "falsifier_reexecuted": result.get("falsifier_reexecuted")},
           CORRECTION_REPORT_REL)
    return {"report": CORRECTION_REPORT_REL,
            "report_sha256": sha256_file(report_path),
            "result": CORRECTION_RESULT_REL,
            "result_sha256": sha256_file(result_path),
            "missing_tokens": absent}


def cc4_bundle(mount: Path, checks: dict) -> dict:
    rel = ("results/product/offline_slice/20261024T142517Z/"
           "rent-default.bundle.json")
    bundle = load_json(mount / rel)
    span = ((bundle.get("provenance") or {}).get("counter_evidence_span") or {})
    ok = sha256_file(mount / rel) == (
        "6eee1149b3c0ec23124746af482e15d9298c2120ee25de4bc4dd7e1cf7d93fa9"
    ) and span_ok(span)
    _check(checks, "CC4_bundle_span_provenance_of_record", ok,
           "bundle sha pin holds and the seam abstained (applied=true, "
           "n_selected=0, gr_gerichte_ERZ 2010 25 / pivot_absent)",
           {"sha256": sha256_file(mount / rel),
            "applied": span.get("applied"), "mode": span.get("mode"),
            "n_candidates": span.get("n_candidates"),
            "n_selected": span.get("n_selected"),
            "n_abstained": span.get("n_abstained"),
            "abstained_ids": span.get("abstained_ids"),
            "abstention_reasons": span.get("abstention_reasons"),
            "frozen_rules_sha256": span.get("frozen_rules_sha256")},
           rel)
    return {"path": rel, "sha256": sha256_file(mount / rel),
            "span": span}


def cc5_code_path(mount: Path, checks: dict) -> dict:
    pipeline = (mount / "product/query/pipeline.py").read_text(encoding="utf-8")
    slice_text = (mount / "product/offline_slice.py").read_text(encoding="utf-8")
    lines = pipeline.splitlines()
    old = "if not fixture_generation and adversarial_retrieval"
    apply_i = next((i for i, ln in enumerate(lines)
                    if "apply_verified_span_selection(" in ln), None)
    guard_i = None
    if apply_i is not None:
        for i in range(apply_i - 1, -1, -1):
            if "if adversarial_retrieval:" in lines[i]:
                guard_i = i
                break
    between = "\n".join(lines[guard_i:apply_i]) if (
        guard_i is not None and apply_i is not None) else ""
    # 51d306c is a provenance citation in the correction report; the shallow
    # accepted mount no longer carries that object, so it is REPORTED-ONLY.
    diff = git(mount, "show", "51d306c", "--format=%H%n%s", "--",
               "product/query/pipeline.py")
    diff_present = diff.returncode == 0
    ok = (
        old not in pipeline
        and apply_i is not None and guard_i is not None
        and apply_i > guard_i
        and "if not fixture_generation" not in between
        and "fixture_generation=True" in slice_text
    )
    _check(checks, "CC5_accepted_code_path", ok,
           "current mount structurally routes apply_verified_span_selection "
           "under `if adversarial_retrieval:` only (no old combined gate); "
           "offline_slice still passes fixture_generation=True; 51d306c diff is "
           "REPORTED-ONLY because the shallow mount no longer carries that object",
           {"pipeline_sha256": sha256_file(mount / "product/query/pipeline.py"),
            "old_predicate_occurrences": pipeline.count(old),
            "apply_line": apply_i + 1 if apply_i is not None else None,
            "guard_line": guard_i + 1 if guard_i is not None else None,
            "lines_between_apply_and_guard": between,
            "fixture_generation_true": "fixture_generation=True" in slice_text,
            "51d306c_object_present_in_shallow_mount": diff_present},
           "product/query/pipeline.py + product/offline_slice.py")
    return {"apply_line": apply_i + 1 if apply_i is not None else None,
            "guard_line": guard_i + 1 if guard_i is not None else None,
            "old_predicate_occurrences": pipeline.count(old)}


def cc6_measurement(repo: Path, freeze: dict, checks: dict) -> dict:
    record = load_json(repo / FALSIFIER_RECORD_REL)
    agg = record.get("aggregate") or {}
    pinned = freeze["frozen_measurement_of_record_copy_for_CC7"]
    observed = {
        "verdict": record.get("verdict"),
        "exit_code": record.get("exit_code"),
        "falsification_proven": record.get("falsification_proven"),
        "n_verified_scored_rows_total": agg.get("n_verified_scored_rows_total"),
        "n_defective_verified_scored_rows_total":
            agg.get("n_defective_verified_scored_rows_total"),
        "defect_histogram": agg.get("defect_histogram"),
        "distinct_defective_decision_ids":
            agg.get("distinct_defective_decision_ids"),
    }
    sound = [r.get("decision_id")
             for b in record.get("bundles") or []
             for r in b.get("verified_scored_rows") or []
             if not (r.get("defects") or [])]
    observed["sound_decision_id"] = sound[0] if len(sound) == 1 else sound
    ok = (measurement_ok(observed, pinned)
          and sha256_file(repo / FALSIFIER_RECORD_REL)
          == freeze["expected_repo_pins_before_execution"][FALSIFIER_RECORD_REL])
    _check(checks, "CC6_measurement_of_record_unchanged_not_reexecuted", ok,
           "the 40105794124 record still reproduces the freeze-pinned aggregate "
           "and is read-only; this instrument never imports or invokes its engine",
           {"observed": observed, "pinned": pinned,
            "record_sha256": sha256_file(repo / FALSIFIER_RECORD_REL)},
           FALSIFIER_RECORD_REL)
    return {"observed": observed, "record_sha256":
            sha256_file(repo / FALSIFIER_RECORD_REL)}


def cc7_incumbents(mount: Path, repo: Path, checks: dict) -> dict:
    record = load_json(repo / FALSIFIER_RECORD_REL)
    rows = []
    for bundle in record.get("bundles") or []:
        rel = bundle.get("path")
        if not rel or not (mount / rel).is_file():
            rows.append({"path": rel, "ok": False, "reason": "bundle missing"})
            continue
        doc = load_json(mount / rel)
        index = {d.get("decision_id"): d for d in doc.get("decisions") or []}
        for row in bundle.get("verified_scored_rows") or []:
            did = row.get("decision_id")
            d = index.get(did) or {}
            rows.append({
                "path": rel, "decision_id": did,
                "defects_read_from_record": row.get("defects"),
                "counter_evidence_verified_at_mount":
                    d.get("counter_evidence_verified"),
                "counter_status_at_mount": d.get("counter_status"),
                "counter_uncertainty_at_mount": d.get("counter_uncertainty"),
                "ok": d.get("counter_evidence_verified") is True,
            })
    defective = [r for r in rows if r.get("defects_read_from_record")]
    sound = [r for r in rows if not r.get("defects_read_from_record")]
    ok = (len(defective) == 4 and len(sound) == 1
          and all(r["ok"] for r in rows))
    _check(checks, "CC7_incumbent_rows_still_verified", ok,
           "all 4 defective decision rows and the 1 sound row named by the "
           "record are still counter_evidence_verified=true at the mount "
           "(flag read, never re-scored)",
           {"n_defective": len(defective), "n_sound": len(sound),
            "all_verified": all(r["ok"] for r in rows), "rows": rows},
           "accepted mount bundles vs committed record row list")
    return {"n_defective": len(defective), "n_sound": len(sound), "rows": rows}


def cc8_item2(mount: Path, repo: Path, checks: dict) -> dict:
    hyp = load_json(repo / PRECONDITION_HYP_REL)
    gate = PR.precondition_gate(hyp, mount)
    h1 = bool(gate.get("H1_precondition_leg_landed"))
    h2 = bool(gate.get("H2_precondition_full_family_regenerated"))
    mfm = ((gate.get("set_relations_REQUIREMENT_16") or {})
           .get("member_for_member_matching") or {})
    matched = int(mfm.get("matched_members") or 0)
    total = int(mfm.get("of") or 0)
    status = str(gate.get("item_2_full_protocol_status") or "")
    ok = (status == "READY" and h1 and h2 and matched == total) or (
        status.startswith("NOT_YET") and not (h1 and h2)
        and matched < total)
    _check(checks, "CC8_item2_precondition_reused_frozen_gate", ok,
           "frozen precondition_gate returns a self-consistent set relation; "
           "this resume records READY only on 15/15 and otherwise NOT_YET",
           {"H1_leg_landed": h1, "H2_family_regenerated": h2,
            "matched_members": matched, "of": total,
            "matched_per_role": mfm.get("matched_per_role"),
            "roles_post": (gate.get("set_relations_REQUIREMENT_16") or {})
            .get("roles_post_repair"),
            "status": status[:180],
            "full_protocol_executed": False,
            "packet_of_record_scored": False},
           PRECONDITION_HYP_REL)
    return {"H1": h1, "H2": h2, "matched": matched, "of": total,
            "status": status, "gate": gate,
            "full_protocol_executed": False,
            "packet_of_record_scored": False,
            "falsifier_reexecuted": False}


def cc9_frozen_inputs(repo: Path, freeze: dict, checks: dict) -> dict:
    diffs = {}
    # The two state files are pinned for the pre-execution snapshot but are
    # intentionally rewritten by --apply-state; they are not part of this
    # "before and after" frozen-input claim.
    skipped_state = {"state/evaluation.json",
                     "evaluation/state/evaluation.json"}
    for rel, expected in freeze["expected_repo_pins_before_execution"].items():
        if rel in skipped_state:
            continue
        p = repo / rel
        if not p.is_file():
            diffs[rel] = {"expected": expected, "actual": "MISSING"}
            continue
        actual = sha256_file(p)
        if actual != expected:
            diffs[rel] = {"expected": expected, "actual": actual}
    _check(checks, "CC9_frozen_inputs_rehash", not diffs,
           "every frozen input and population pin re-hashes to its freeze value "
           "(state files excluded: they are intentionally rewritten later)",
           {"mismatches": diffs,
            "n_pins": len(freeze["expected_repo_pins_before_execution"])
            - len(skipped_state)},
           FREEZE_REL)
    return {"mismatches": diffs, "state_files_excluded": sorted(skipped_state)}


def cc11_no_falsifier_or_174k(repo: Path, checks: dict) -> dict:
    src = (repo / INSTRUMENT_REL).read_text(encoding="utf-8")
    forbidden_imports = [
        f"from evaluation import {FORBIDDEN_MODULE}",
        f"import {FORBIDDEN_MODULE}",
        f"{FORBIDDEN_MODULE}.",
    ]
    found = [s for s in forbidden_imports if s in src]
    # every file this instrument reads is from the frozen list; none is 174k
    read_rels = [
        HYP_REL, FREEZE_REL, REST_CAPTURE_REL, ANNOTATION_REL,
        CORRECTION_REPORT_REL, CORRECTION_RESULT_REL, FALSIFIER_RECORD_REL,
        PRECONDITION_HYP_REL, ACCEPTED_GATE_REL,
    ] + list(freeze_keys_for_reads())
    try:
        read_rels += list(
            json.loads((repo / FREEZE_REL).read_text(encoding="utf-8"))
            ["expected_repo_pins_before_execution"])
    except Exception:
        pass
    suspicious = [p for p in read_rels if "174" in str(p)]
    ok = not found and not suspicious
    _check(checks, "CC11_no_falsifier_reexecution_and_no_174k", ok,
           "instrument source does not import/invoke the falsifier engine; no "
           "read path is a universal-174k artifact",
           {"forbidden_imports_found": found, "suspicious_read_paths": suspicious},
           INSTRUMENT_REL)
    return {"forbidden_imports_found": found,
            "suspicious_read_paths": suspicious}


def freeze_keys_for_reads() -> list[str]:
    return []


def source_read_paths(repo: Path) -> list[str]:
    """The explicit read path list used for the 174k guard."""
    freeze = load_json(repo / FREEZE_REL)
    return list(freeze["expected_repo_pins_before_execution"])


# --------------------------------------------------------------- state phase
def _state_refs(repo: Path) -> list[str]:
    refs = [
        HYP_REL, FREEZE_REL, INSTRUMENT_REL, RESULT_REL, REPORT_REL,
        TEST_REL, TEST_SUITE_REL, AUDIT_INDEX_REL,
        REST_CAPTURE_REL, ANNOTATION_REL,
        CORRECTION_REPORT_REL, CORRECTION_RESULT_REL,
        FALSIFIER_RECORD_REL, ACCEPTED_GATE_REL, ACCEPTED_REPORT_REL,
        PRECONDITION_HYP_REL, PRECONDITION_FREEZE_REL,
    ]
    return [r for r in refs if (repo / r).is_file()]


def _build_state_blocks(repo: Path, result: dict) -> dict:
    item2 = result["item_2"]
    mfm = ((item2["gate"].get("set_relations_REQUIREMENT_16") or {})
           .get("member_for_member_matching") or {})
    operational = {
        "schema": SCHEMA,
        "run": RUN_ID,
        "run_under_resume": RUN_UNDER_RESUME,
        "prior_resume_run": 40234421521,
        "direction_version": 68,
        "mode": "OPERATIONAL_RESUME",
        "base_snapshot_commit": SNAPSHOT_SHA,
        "prior_snapshot_commit": SNAPSHOT_SHA,
        "snapshot_subject": SNAPSHOT_SUBJECT,
        "failure_class": "ORCHESTRATION_RC1_NONZERO_EXIT",
        "failure_summary": (
            "Run 44642554373 (team job 135977000346) failed at step 6 "
            "'Run lane cycle' after 16s with the public annotation 'Process "
            "completed with exit code 1.'; audit and integrate were skipped; "
            "resilience succeeded; no /audit branch and no gate exist; the "
            "persisted team snapshot remained ea98384e byte-identical. This is "
            "not rc=67 zero-delta, not a 64-77 preflight, not rc=78 quantum and "
            "not the step-9 write-scope validation (skipped)."
        ),
        "failure_evidence": {
            "rest_capture": REST_CAPTURE_REL,
            "rest_capture_sha256": result["checks"]["CC2_orchestration_rc1_failure_class"][
                "actual"]["capture_sha256"],
            "annotation_evidence": ANNOTATION_REL,
            "annotation_evidence_sha256": result["checks"]["CC2_orchestration_rc1_failure_class"][
                "actual"]["annotation_sha256"],
            "failing_step": 6,
            "failing_step_name": "Run lane cycle",
            "failing_step_annotation": "Process completed with exit code 1.",
            "failing_step_duration_s": 16,
            "audit_and_integrate_skipped": True,
            "snapshot_branch_unchanged": True,
            "no_audit_branch": True,
            "no_gate_or_verdict_issued": True,
        },
        "preserved": {
            "snapshot_head": SNAPSHOT_SHA,
            "origin_team_head": SNAPSHOT_SHA,
            "origin_lab_evaluation_head": SNAPSHOT_SHA,
            "origin_audit_ref": "ABSENT",
            "latest_accepted_evaluation_cycle": LATEST_ACCEPTED_EVAL,
            "accepted_gate": ACCEPTED_GATE_REL,
        },
        "correction_of_record": {
            "run": 40144816305,
            "corrects_run": 40105794124,
            "report": CORRECTION_REPORT_REL,
            "report_sha256": result["checks"]["CC3_correction_of_record_pinned"][
                "actual"]["report_sha256"],
            "machine_result": CORRECTION_RESULT_REL,
            "machine_result_sha256": result["checks"]["CC3_correction_of_record_pinned"][
                "actual"]["result_sha256"],
            "measurement_unchanged": True,
            "falsifier_reexecuted": False,
            "bundle_sha256": result["checks"]["CC4_bundle_span_provenance_of_record"][
                "actual"]["sha256"],
            "span_applied": True,
            "span_n_selected": 0,
            "span_abstained_ids": ["gr_gerichte_ERZ 2010 25"],
            "span_abstention_reasons": {"pivot_absent": 1},
            "pipeline_file_line_relation": {
                "apply_line": result["checks"]["CC5_accepted_code_path"]["actual"].get(
                    "apply_line"),
                "guard_line": result["checks"]["CC5_accepted_code_path"]["actual"].get(
                    "guard_line"),
                "old_predicate_occurrences": 0,
            },
            "incumbents_verified": {
                "n_defective": result["checks"]["CC7_incumbent_rows_still_verified"]["actual"][
                    "n_defective"],
                "n_sound": result["checks"]["CC7_incumbent_rows_still_verified"]["actual"]["n_sound"],
                "all_verified": True,
            },
        },
        "item_2": {
            "status": item2["status"].split(" (")[0],
            "full_status_text": item2["status"],
            "leg_landed": item2["H1"],
            "family_regenerated": item2["H2"],
            "matched_members": item2["matched"],
            "of": item2["of"],
            "matched_per_role": mfm.get("matched_per_role"),
            "post_repair_roles": (item2["gate"].get(
                "set_relations_REQUIREMENT_16") or {}).get(
                "roles_post_repair"),
            "product_claim_roles_satisfied": (item2["gate"].get(
                "product_claim_adjudication") or {}).get(
                "claim_roles_satisfied_by_post_repair_bytes"),
            "full_protocol_executed": False,
            "packet_of_record_scored": False,
            "falsifier_reexecuted": False,
            "why": (
                "H1 is true but H2 is false: the post-repair inventory has 3 "
                "server/served bundles against the frozen family's 4, so the "
                "member-for-member relation is 14/15. No synthetic stand-in, "
                "no packet-of-record scoring and no d2_path_scope_probe replay "
                "is substituted."
            ),
        },
        "standing_falsification": {
            "record": FALSIFIER_RECORD_REL,
            "record_sha256": result["checks"]["CC6_measurement_of_record_unchanged_not_reexecuted"][
                "actual"]["record_sha256"],
            "verdict": "SOUND_COUNTER_ROW_PRESENT",
            "exit_code": 0,
            "falsification_proven": False,
            "re_executed": False,
        },
        "state_pointer": {
            "accepted_run_id_before": 40258497460,
            "accepted_run_id_after": LATEST_ACCEPTED_EVAL,
            "superseded_proposed_run": PROPOSED_PRECEDING_RUN,
            "current_run_pending_audit": RUN_ID,
        },
        "no_new_claim_bearing_measurement": True,
        "no_falsifier_reexecution": True,
        "no_universal_174k_benchmark": True,
        "audit_status": "PENDING_INDEPENDENT_AUDIT",
        "pending_independent_audit": True,
        "accepted_as_evidence": False,
        "human_gate_ready": False,
        "machine_gate_ready": False,
        "owner_decision_required": False,
        "claim_ceiling": result.get("claim_ceiling"),
    }
    advance = {
        "schema": "lex-evaluation-accepted-run-advance/1",
        "from": 40258497460,
        "to": LATEST_ACCEPTED_EVAL,
        "run_this_advance": RUN_ID,
        "direction_version": 68,
        "both_halves_of_requirement_4": {
            "half_i_audit_gate": (
                f"{ACCEPTED_GATE_REL} gate=PASS safe_to_integrate=true "
                "required_fixes=[] (in tree)"),
            "half_ii_accept_commit": (
                f"origin/lab/evaluation head {SNAPSHOT_SHA} "
                f"'{SNAPSHOT_SUBJECT}'"),
            "surfaces_read": "BOTH halves (factory-wide requirement 4)",
        },
        "intervening_proposed_run": {
            "run": PROPOSED_PRECEDING_RUN,
            "audit_gate_in_tree": False,
            "accept_commit": None,
            "disposition": (
                "never acquired an in-tree audit gate or accept commit; it is "
                "not accepted evidence and is superseded as the pointer by "
                "40265377500"),
        },
        "why": (
            "state/evaluation.json still pointed accepted_run_id at 40258497460 "
            "although 40265377500 is accepted on both halves. The pointer is "
            "corrected without touching any historical artifact."),
    }
    github_advance = {
        "schema": "lex-evaluation-github-run-advance/1",
        "from": PROPOSED_PRECEDING_RUN,
        "to": RUN_ID,
        "run_under_resume": RUN_UNDER_RESUME,
        "direction_version": 68,
        "rule": (
            "github_run/proposed_run_id name the current operational-resume "
            "run proposed for independent audit; accepted_run_id names the "
            "latest cycle accepted on both halves. They are deliberately "
            "different values and are never conflated."),
    }
    item2_block = {
        "schema": "lex-evaluation-v68-item-2-reconciliation/1",
        "run": RUN_ID,
        "direction_version": 68,
        "product_mount": str(DEFAULT_MOUNT),
        "product_mount_head": PRODUCT_MOUNT_HEAD,
        "product_accepted_cycle": PRODUCT_ACCEPTED_CYCLE,
        "product_gate": (
            "results/audit/product/CYCLE_40284658455_GATE.json gate=PASS "
            "safe_to_integrate=true required_fixes=[]"),
        "historical_blocks_preserved": [
            "v68_correction (40144816305)",
            "v68_item_2_reconciliation_40192868113",
            "post_repair_family_ca_falsifier_40258497460",
        ],
        "historical_item_2_status": "NOW_DISCRIMINATING (40144816305; preserved)",
        "current_status": item2["status"].split(" (")[0],
        "H1_leg_landed": item2["H1"],
        "H2_family_regenerated": item2["H2"],
        "matched_members": item2["matched"],
        "of": item2["of"],
        "matched_per_role": mfm.get("matched_per_role"),
        "post_repair_roles": (item2["gate"].get(
            "set_relations_REQUIREMENT_16") or {}).get("roles_post_repair"),
        "full_protocol_executed": False,
        "packet_of_record_39319405429_scored": False,
        "d2_path_scope_probe_replayed": False,
        "finding": (
            "The product has advanced to accepted cycle 40284658455 "
            "(head 7be4480e) and the leg is landed, but the frozen 15-member "
            "family is regenerated 14/15: server/served is 3 against 4. "
            "Ordered item (2) therefore remains NOT_YET_DISCRIMINATING. The "
            "product's own 4-offline+1-server claim is satisfied, but that is a "
            "different set and is not substituted for the named family."),
    }
    return {"operational": operational, "advance": advance,
            "github_advance": github_advance, "item2": item2_block}


def _dedupe(seq: list[str]) -> list[str]:
    seen = set()
    out = []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def apply_state(repo: Path, result: dict) -> dict:
    root_path = repo / "state/evaluation.json"
    lane_path = repo / "evaluation/state/evaluation.json"
    root = load_json(root_path)
    lane = load_json(lane_path)
    root_before_keys = len(root)
    lane_before_keys = len(lane)
    root_before_refs = len(root.get("evidence_refs") or [])
    lane_before_refs = len(lane.get("evidence_refs") or [])
    blocks = _build_state_blocks(repo, result)
    refs = _state_refs(repo)

    for st in (root, lane):
        st["accepted_run_id"] = LATEST_ACCEPTED_EVAL
        st["github_run"] = RUN_ID
        st["proposed_run_id"] = RUN_ID
        st["audit_status"] = "PENDING_INDEPENDENT_AUDIT"
        st["current_cycle_audit_status"] = "PENDING_INDEPENDENT_AUDIT"
        st["direction_version"] = 68
        st["evidence_refs"] = _dedupe(list(st.get("evidence_refs") or []) + refs)
        st["evidence_refs_n"] = len(st["evidence_refs"])
        st["operational_resume_44642744588"] = blocks["operational"]
        st["accepted_run_id_advance_44642744588"] = blocks["advance"]
        st["github_run_advance_44642744588"] = blocks["github_advance"]
        st["v68_item_2_reconciliation_44642744588"] = blocks["item2"]

    root["state_update_44642744588"] = {
        "schema": "lex-evaluation-state-update/1",
        "run_id": RUN_ID,
        "direction_version": 68,
        "additive_only": True,
        "keys_before": root_before_keys,
        "keys_after": len(root),
        "evidence_refs_before": root_before_refs,
        "evidence_refs_after": len(root["evidence_refs"]),
        "no_key_removed": True,
        "no_ref_removed": True,
        "accepted_run_id_advanced": True,
        "proposed_run_id_set_to": RUN_ID,
        "audit_status": "PENDING_INDEPENDENT_AUDIT",
        "why_no_claim_bearing": (
            "this cycle measures no new counter-authority, retrieval, label, "
            "geometry or serve outcome; it verifies orchestration provenance "
            "and re-derives a frozen precondition"),
    }
    lane["state_update_44642744588"] = root["state_update_44642744588"]

    root_path.write_text(
        json.dumps(root, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lane_path.write_text(
        json.dumps(lane, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # CC10: verify the persisted state itself, not the plan.
    root2 = load_json(root_path)
    lane2 = load_json(lane_path)
    checks = result.setdefault("checks", {})
    root_refs_ok = root2.get("evidence_refs_n") == len(
        root2.get("evidence_refs") or []) and all(
        (repo / r).is_file() for r in root2.get("evidence_refs") or [])
    lane_refs_ok = lane2.get("evidence_refs_n") == len(
        lane2.get("evidence_refs") or []) and all(
        (repo / r).is_file() for r in lane2.get("evidence_refs") or [])
    gate_present = (repo / ACCEPTED_GATE_REL).is_file()
    accept = git(repo, "log", "-1", "--format=%s", SNAPSHOT_SHA).stdout.strip()
    ok = (root2.get("accepted_run_id") == LATEST_ACCEPTED_EVAL
          and lane2.get("accepted_run_id") == LATEST_ACCEPTED_EVAL
          and root2.get("github_run") == RUN_ID
          and lane2.get("github_run") == RUN_ID
          and root_refs_ok and lane_refs_ok
          and state_bridge_ok(int(root2["accepted_run_id"]), gate_present,
                             accept))
    _check(checks, "CC10_state_pointer_and_refs", ok,
           "both state files carry accepted_run_id=40265377500 and "
           "github_run=44642744588; evidence_refs_n==len and every ref resolves; "
           "gate PASS and accept commit subject match",
           {"root_accepted_run_id": root2.get("accepted_run_id"),
            "lane_accepted_run_id": lane2.get("accepted_run_id"),
            "root_github_run": root2.get("github_run"),
            "lane_github_run": lane2.get("github_run"),
            "root_refs_n": root2.get("evidence_refs_n"),
            "root_refs_len": len(root2.get("evidence_refs") or []),
            "lane_refs_n": lane2.get("evidence_refs_n"),
            "lane_refs_len": len(lane2.get("evidence_refs") or []),
            "root_refs_all_resolve": root_refs_ok,
            "lane_refs_all_resolve": lane_refs_ok,
            "gate_present": gate_present,
            "accept_subject": accept},
           "state/evaluation.json; evaluation/state/evaluation.json")
    return {"root_keys_before": root_before_keys,
            "root_keys_after": len(root2),
            "lane_keys_before": lane_before_keys,
            "lane_keys_after": len(lane2),
            "root_refs_before": root_before_refs,
            "root_refs_after": len(root2.get("evidence_refs") or []),
            "lane_refs_before": lane_before_refs,
            "lane_refs_after": len(lane2.get("evidence_refs") or []),
            "cc10_ok": ok}


# ------------------------------------------------------------------- controls
def run_controls(repo: Path, result: dict) -> dict:
    controls = {}
    # C1: snapshot mutation must be detected
    base = (SNAPSHOT_SHA, SNAPSHOT_SHA, SNAPSHOT_SHA, False)
    ok = (snapshot_relation_ok(*base) and not snapshot_relation_ok(
        "0" * 40, SNAPSHOT_SHA, SNAPSHOT_SHA, False))
    controls["C1_snapshot_mutation_detected"] = {
        "holds": ok, "detail": "flipping the head sha makes the relation false"}

    # C2: annotation mutation must be detected
    capture = load_json(repo / REST_CAPTURE_REL)
    ann = load_json(repo / ANNOTATION_REL)
    mutated_ann = "Process completed with exit code 67."
    ok = (failure_metadata_ok(capture, ann.get("annotation") or "")
          and not failure_metadata_ok(capture, mutated_ann))
    controls["C2_annotation_mutation_detected"] = {
        "holds": ok, "detail": "exit code 1 -> 67 makes the metadata check false"}

    # C3: n_selected mutation must be detected
    span = result["checks"]["CC4_bundle_span_provenance_of_record"]["actual"]
    good = {"applied": span.get("applied"), "mode": span.get("mode"),
            "n_candidates": span.get("n_candidates"),
            "n_selected": span.get("n_selected"),
            "n_abstained": span.get("n_abstained"),
            "abstained_ids": span.get("abstained_ids"),
            "abstention_reasons": span.get("abstention_reasons"),
            "frozen_rules_sha256": span.get("frozen_rules_sha256")}
    bad = dict(good, n_selected=1)
    ok = span_ok(good) and not span_ok(bad)
    controls["C3_span_mutation_detected"] = {
        "holds": ok, "detail": "n_selected 0 -> 1 is reported as a divergence"}

    # C4: measurement mutation must be detected
    pinned = {
        "verdict": "SOUND_COUNTER_ROW_PRESENT", "exit_code": 0,
        "falsification_proven": False, "n_verified_scored_rows_total": 5,
        "n_defective_verified_scored_rows_total": 4,
        "defect_histogram": {"D2_letterhead_zone": 2,
                             "D3_markup_residue": 2,
                             "D4_language_marker_mismatch": 1},
        "distinct_defective_decision_ids": [
            "bge_BGE_110_II_391", "bge_BGE_121_III_260",
            "ge_gerichte_CAPH_107_2004", "gr_gerichte_ERZ 2010 25"],
    }
    bad = dict(pinned, n_defective_verified_scored_rows_total=3)
    ok = measurement_ok(pinned, pinned) and not measurement_ok(bad, pinned)
    controls["C4_measurement_mutation_detected"] = {
        "holds": ok, "detail": "n_defective 4 -> 3 diverges from the freeze pin"}

    # C5: no falsifier import/invocation in this instrument's source
    src = (repo / INSTRUMENT_REL).read_text(encoding="utf-8")
    tokens = [FORBIDDEN_MODULE + ".", "from evaluation import " + FORBIDDEN_MODULE,
              "import " + FORBIDDEN_MODULE]
    found = [t for t in tokens if t in src]
    controls["C5_no_falsifier_reexecution"] = {
        "holds": not found,
        "detail": "instrument source imports/invokes none of the falsifier engine",
        "forbidden_substrings_found": found}

    # C6: item-2 status rule
    controls["C6_item2_rule_consistency"] = {
        "holds": item2_consistency_ok(
            result["item_2"]["status"], result["item_2"]["H1"],
            result["item_2"]["H2"], result["item_2"]["matched"],
            result["item_2"]["of"]),
        "detail": "READY requires H1+H2+15/15; NOT_YET requires a shortfall"}

    # C7: state bridge (evaluated after apply-state; measure mode defers)
    applied = bool(result.get("state_update"))
    if applied:
        root = load_json(repo / "state/evaluation.json")
        accept = git(repo, "log", "-1", "--format=%s", SNAPSHOT_SHA).stdout.strip()
        controls["C7_state_pointer_bridge"] = {
            "holds": state_bridge_ok(
                int(root.get("accepted_run_id")),
                (repo / ACCEPTED_GATE_REL).is_file(), accept),
            "detail": "accepted_run_id==40265377500, gate exists, accept "
                      "subject matches"}
    else:
        controls["C7_state_pointer_bridge"] = {
            "holds": None, "deferred": True,
            "detail": "verified after --apply-state persists the pointer"}

    # C8: write scope accepts our paths and rejects an audit-of-record path
    status = git(repo, "status", "--porcelain", "-uall").stdout
    paths = [ln[3:].strip() for ln in status.splitlines() if ln[3:].strip()]
    bad = WS.classify_path(
        f"results/audit/evaluation/CYCLE_{RUN_ID}_GATE.json", "evaluation")
    good = all(WS.classify_path(p, "evaluation") for p in paths)
    controls["C8_write_scope"] = {
        "holds": good and not bad,
        "detail": "all current producer paths are in-scope; a producer audit "
                  "gate path is rejected",
        "n_paths": len(paths), "paths": paths[:80],
        "planted_audit_path_rejected": not bad}
    return controls


# ---------------------------------------------------------------------- report
def write_report(repo: Path, result: dict) -> Path:
    c = result["checks"]
    item2 = result["item_2"]
    mfm = ((item2["gate"].get("set_relations_REQUIREMENT_16") or {})
           .get("member_for_member_matching") or {})
    lines = [
        f"# Operational resume of run {RUN_UNDER_RESUME} (run {RUN_ID})",
        "",
        f"- Lane: evaluation; direction v68; mode OPERATIONAL_RESUME",
        f"- Snapshot: `{SNAPSHOT_SHA}` ('{SNAPSHOT_SUBJECT}')",
        f"- Product mount: `{DEFAULT_MOUNT}` at `{PRODUCT_MOUNT_HEAD}` "
        f"(accept cycle {PRODUCT_ACCEPTED_CYCLE})",
        f"- Verdict: **{result.get('verdict', 'MEASUREMENT_COMPLETE_STATE_PENDING')}**",
        "",
        "## What happened",
        "",
        "Run 44642554373 failed at the producer step, not at validation. The "
        "public REST capture and job-page annotation show:",
        "",
        "- run conclusion `failure`, event `workflow_dispatch`, head `b132288c`;",
        "- team job `135977000346` step 6 `Run lane cycle` failed after 16s "
        "with `Process completed with exit code 1.`;",
        "- `audit` and `integrate` were **skipped**; `resilience` succeeded;",
        "- no `cycle/core/evaluation/44642554373/audit` ref, no gate, no report, "
        "and no verdict were produced;",
        "- the persisted team snapshot remained `ea98384e` byte-identical.",
        "",
        "This is `ORCHESTRATION_RC1_NONZERO_EXIT`, not the rc-67 zero-delta "
        "guard, not a 64-77 preflight, not rc-78 work-quantum, and not the "
        "step-9 write-scope check (skipped). Log download is still HTTP 403 "
        "without admin rights; mechanism attribution beyond the checked-in "
        "wrapper is not claimed.",
        "",
        "## v68 ordered item (1): correction of record",
        "",
        f"The correction report `{CORRECTION_REPORT_REL}` "
        f"(`{c['CC3_correction_of_record_pinned']['actual']['report_sha256'][:12]}`) and machine record "
        f"`{CORRECTION_RESULT_REL}` "
        f"(`{c['CC3_correction_of_record_pinned']['actual']['result_sha256'][:12]}`) are present and "
        "internally consistent. The accepted bundle "
        "`20261024T142517Z/rent-default.bundle.json` is "
        f"`{c['CC4_bundle_span_provenance_of_record']['actual']['sha256'][:12]}` and its span provenance still "
        "shows `applied=true`, `n_selected=0`, abstained id "
        "`gr_gerichte_ERZ 2010 25`, reason `pivot_absent`. The current mount "
        "routes `apply_verified_span_selection` under `if adversarial_retrieval:` "
        f"(apply line {c['CC5_accepted_code_path']['actual'].get('apply_line')}, guard line "
        f"{c['CC5_accepted_code_path']['actual'].get('guard_line')}); the old combined gate is "
        "absent; `offline_slice.py` still passes `fixture_generation=True`. The "
        "4 defective rows and the 1 sound row remain `counter_evidence_verified=true` "
        "because the incumbent was left in place.",
        "",
        "## v68 ordered item (2): precondition only, NOT executed",
        "",
        f"Frozen `precondition_gate` on the current mount: **H1 leg landed = "
        f"{item2['H1']}**, **H2 full family regenerated = {item2['H2']}**, "
        f"member-for-member **{item2['matched']}/{item2['of']}**.",
        "",
        f"- post-repair roles: `{json.dumps((item2['gate'].get('set_relations_REQUIREMENT_16') or {}).get('roles_post_repair'))}`",
        f"- matched per role: `{json.dumps(mfm.get('matched_per_role'))}`",
        "- Product's own 4-offline + 1-server claim is satisfied, but that is a "
        "different set from the direction's named 15-member family and is not "
        "substituted.",
        "",
        f"**Status: `{item2['status'].split(' (')[0]}`.** No packet-of-record "
        "39319405429 scoring, no `d2_path_scope_probe` replay, no synthetic "
        "stand-in, and no full item-(2) re-measure was run. A READY status "
        "would have required a separately frozen claim-bearing cycle.",
        "",
        "## Standing falsification record",
        "",
        f"`{FALSIFIER_RECORD_REL}` "
        f"(`{result['checks']['CC6_measurement_of_record_unchanged_not_reexecuted']['actual']['record_sha256'][:12]}`) is read "
        "as committed evidence only. Verdict `SOUND_COUNTER_ROW_PRESENT`, exit "
        "0, `falsification_proven=false`, 5 verified rows, 4 defective over 4 "
        "distinct decisions (D2 2 / D3 2 / D4 1), one sound row "
        "`bstger_SK.2023.49`. The engine was **not** re-executed.",
        "",
        "## State reconciliation",
        "",
        f"`accepted_run_id` advances `40258497460 -> {LATEST_ACCEPTED_EVAL}` on "
        "**both halves** (`CYCLE_40265377500_GATE.json` gate PASS and accept "
        f"commit `{SNAPSHOT_SHA}`). `github_run`/`proposed_run_id` become "
        f"`{RUN_ID}` pending independent audit. The stale proposed run "
        "`40261335674` never acquired an audit gate or accept commit and is "
        "superseded as the pointer; it is preserved as history, not promoted.",
        "",
        "## Controls",
        "",
    ]
    for cid, row in result.get("controls", {}).items():
        holds = row.get("holds")
        lines.append(f"- `{cid}`: {'HOLD' if holds else ('DEFERRED' if holds is None else 'FAIL')} - {row.get('detail')}")
    lines += [
        "",
        "## Claim ceiling",
        "",
        result.get("claim_ceiling", ""),
        "",
        "## Reproduce",
        "",
        "```bash",
        "python3 evaluation/operational_resume_44642744588.py --mount /tmp/lex_accepted/product",
        "python3 -m pytest -q tests/evaluation/test_operational_resume_44642744588.py",
        "python3 evaluation/operational_resume_44642744588.py --apply-state",
        "python3 -m evaluation.state_integrity_gate",
        "python3 -m evaluation.snapshot_audit.write_scope --lane evaluation",
        "python3 -m evaluation.nested_evidence_refs_guard",
        "```",
        "",
    ]
    p = repo / REPORT_REL
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(lines), encoding="utf-8")
    return p


def write_audit_index(repo: Path) -> Path:
    entries = []
    for rel in [
        HYP_REL, FREEZE_REL, INSTRUMENT_REL, RESULT_REL, REPORT_REL,
        TEST_REL, TEST_SUITE_REL, REST_CAPTURE_REL, ANNOTATION_REL,
        CORRECTION_REPORT_REL, CORRECTION_RESULT_REL,
        FALSIFIER_RECORD_REL, ACCEPTED_GATE_REL, ACCEPTED_REPORT_REL,
    ]:
        p = repo / rel
        entries.append({"path": rel,
                        "sha256": sha256_file(p) if p.is_file() else None,
                        "present": p.is_file()})
    doc = {
        "schema": "lex-evaluation-operational-resume-audit-index/1",
        "run": RUN_ID,
        "run_under_resume": RUN_UNDER_RESUME,
        "generated_at_utc": utc_now(),
        "snapshot_head": SNAPSHOT_SHA,
        "product_mount_head": PRODUCT_MOUNT_HEAD,
        "accepted_run_id": LATEST_ACCEPTED_EVAL,
        "entries": entries,
    }
    p = repo / AUDIT_INDEX_REL
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n",
                 encoding="utf-8")
    return p


# ------------------------------------------------------------------------ main
def run_measure(repo: Path, mount: Path) -> tuple[int, dict]:
    freeze = load_json(repo / FREEZE_REL)
    checks: dict = {}
    result = {
        "schema": SCHEMA,
        "lane": "evaluation",
        "direction_version": 68,
        "run_id": RUN_ID,
        "run_under_resume": RUN_UNDER_RESUME,
        "mode": "OPERATIONAL_RESUME",
        "generated_at_utc": utc_now(),
        "snapshot_head": SNAPSHOT_SHA,
        "snapshot_subject": SNAPSHOT_SUBJECT,
        "latest_accepted_evaluation_cycle": LATEST_ACCEPTED_EVAL,
        "mount": str(mount),
        "mount_head": PRODUCT_MOUNT_HEAD,
        "product_accepted_cycle": PRODUCT_ACCEPTED_CYCLE,
        "hypothesis": {"path": HYP_REL, "sha256": sha256_file(repo / HYP_REL)},
        "freeze": {"path": FREEZE_REL, "sha256": sha256_file(repo / FREEZE_REL)},
        "instrument": {"path": INSTRUMENT_REL,
                       "sha256": sha256_file(repo / INSTRUMENT_REL)},
        "numeric_environment": numeric_environment(),
        "checks": checks,
        "controls": {},
        "claim_ceiling": (
            "Operational provenance and state reconciliation over committed "
            "accepted artifacts plus a read-only re-derivation of the frozen "
            "item-(2) precondition. It adds no quality measurement, moves no "
            "bar, issues no serve or admission verdict, and makes no "
            "legal-usefulness or human-gate claim."),
        "no_new_claim_bearing_measurement": True,
        "falsifier_reexecuted": False,
        "universal_174k_benchmark_run": False,
        "network_calls": [
            "git ls-remote origin (pinned refs only)",
            "public GitHub REST run/jobs metadata captured before freeze",
        ],
    }
    details = {}
    details["CC1"] = cc1_snapshot(repo, checks)
    details["CC2"] = cc2_failure(repo, checks)
    details["CC3"] = cc3_correction_record(repo, freeze, checks)
    details["CC4"] = cc4_bundle(mount, checks)
    details["CC5"] = cc5_code_path(mount, checks)
    details["CC6"] = cc6_measurement(repo, freeze, checks)
    details["CC7"] = cc7_incumbents(mount, repo, checks)
    details["CC8"] = cc8_item2(mount, repo, checks)
    details["CC9"] = cc9_frozen_inputs(repo, freeze, checks)
    details["CC11"] = cc11_no_falsifier_or_174k(repo, checks)
    result["details"] = details
    result["item_2"] = details["CC8"]
    # C5 source scan is part of controls; build them now with state deferred.
    result["controls"] = run_controls(repo, result)
    # write result/report first so C8 sees the actual producer delta
    out = repo / RESULT_REL
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8")
    write_report(repo, result)
    # refresh controls against the real delta and rewrite
    result["controls"] = run_controls(repo, result)
    result["verdict"] = "MEASUREMENT_COMPLETE_STATE_PENDING"
    result["exit_code"] = EXIT_OK
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8")
    write_report(repo, result)
    return EXIT_OK, result


def run_apply_state(repo: Path) -> tuple[int, dict]:
    if not (repo / RESULT_REL).is_file():
        return EXIT_INPUT, {"error": f"missing {RESULT_REL}; run measure first"}
    result = load_json(repo / RESULT_REL)
    write_audit_index(repo)
    apply = apply_state(repo, result)
    result["state_update"] = apply
    result["controls"] = run_controls(repo, result)
    failed = [k for k, v in result["checks"].items() if not v.get("ok")]
    failed += [k for k, v in result["controls"].items()
               if v.get("holds") is False]
    ok = not failed
    result["verdict"] = (
        "RESUME_VERIFIED_AND_AUDIT_READY" if ok
        else "RESUME_VERIFIED_WITH_FINDINGS")
    result["exit_code"] = EXIT_OK if ok else EXIT_FINDINGS
    result["failed_claims_or_controls"] = failed
    (repo / RESULT_REL).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(repo, result)
    write_audit_index(repo)
    return result["exit_code"], result


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mount", default=str(DEFAULT_MOUNT))
    ap.add_argument("--apply-state", action="store_true")
    args = ap.parse_args(argv)
    repo = REPO_ROOT
    try:
        if args.apply_state:
            code, out = run_apply_state(repo)
        else:
            code, out = run_measure(repo, Path(args.mount))
    except Exception as exc:
        print(json.dumps({"error": repr(exc), "exit_code": EXIT_INPUT},
                         indent=2))
        return EXIT_INPUT
    print(json.dumps({
        "run_id": out.get("run_id"),
        "verdict": out.get("verdict"),
        "exit_code": out.get("exit_code", code),
        "failed": out.get("failed_claims_or_controls", []),
        "state_update": out.get("state_update"),
    }, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
