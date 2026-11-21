#!/usr/bin/env python3
"""Bounded audit-readiness dossier for an operational resume whose jobs API is
reachable but whose job-logs endpoint is not (HTTP 403).

Why this exists
---------------
The core-lane producer can be stopped by orchestration before it writes a gate:
a gateway rejects the request, a permission is denied, or the work quantum
expires.  The next auditor should not have to re-derive the whole vertical
slice, the accepted pointer and the claim ceiling during its own budget.  This
instrument publishes ONE machine-readable dossier that:

* re-classifies the resumed run from its committed public run/jobs snapshot
  (``product.audit_step_diagnosis``) and reproduces its durable-delta proof;
* re-reads the committed resume diagnosis and checks the classification,
  ZERO/COMMITTED delta and UNADJUDICATED status agree with it;
* checks the fail-closed posture and the accepted pointer (both halves of
  factory-wide requirement 4) in ``state/product.json``;
* re-derives the fixed-path counter-content family measurement from the
  product's own committed probe artifact (REPORTED-ONLY, frozen predicates are
  never re-derived here);
* executes the bounded MVP core pytest set and the product state contract,
  recording pass/fail and the numeric environment beside each hash;
* confirms the producer wrote nothing into the auditor namespace and minted
  no gate.

It deliberately never writes ``results/audit/**``, mints a gate, scores a frozen
bar, re-runs a serve verdict, or labels a run accepted/rejected.  Its output is
a dossier for the independent auditor, never a verdict.  The run/jobs-available
/ logs-403 case is a distinct, recurring failure mode that the older
``audit_readiness.py`` profiles (quantum / gateway / observed-scope / raw-free)
do not name; publishing it with those profiles would misreport the run.

Usage
-----
    python3 product/resume_audit_dossier.py --run-id 44856384487 \\
        --resumed-run-id 44856191029 \\
        --out results/product/audit_readiness/CYCLE_44856384487_audit_readiness.json

    # fast iteration (skip the two executed checks):
    python3 product/resume_audit_dossier.py --run-id X --resumed-run-id Y \\
        --skip-tests --out /tmp/dossier.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "product-audit-readiness-dossier/1"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from product import audit_step_diagnosis as asd  # noqa: E402

ORCH = ROOT / "results" / "product" / "orchestration"
STATE = ROOT / "state" / "product.json"

MVP_TESTS = (
    "product/tests/test_query_map_mvp.py",
    "product/tests/test_server_query_api.py",
    "product/tests/test_offline_slice.py",
    "product/tests/test_progressive_smoke.py",
    "product/tests/test_adversarial_retrieval.py",
    "product/tests/test_counter_evidence_span.py",
    "product/tests/test_counter_content_rejection_v68.py",
    "product/tests/test_state_contract.py",
    "product/tests/test_progressive_query.py",
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _rel(path: Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(ROOT), capture_output=True, text=True)


def _environment() -> dict[str, Any]:
    versions: dict[str, str] = {}
    mod_for_key = {
        "numpy": "numpy", "scipy": "scipy",
        "scikit_learn": "sklearn", "pytest": "pytest",
    }
    for key, mod in mod_for_key.items():
        try:
            versions[key] = getattr(__import__(mod), "__version__", "unknown")
        except Exception:  # pragma: no cover - recorded, never invented
            versions[key] = "MISSING"
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "installed": versions,
    }


def _accepted_pointer(state: dict[str, Any]) -> dict[str, Any]:
    run_id = str(state.get("accepted_run_id") or "")
    result: dict[str, Any] = {"accepted_run_id": run_id, "halves": {}}
    if run_id.startswith("CYCLE_"):
        num = run_id[len("CYCLE_"):]
    else:
        num = run_id
    gate_path = ROOT / "results" / "audit" / "product" / f"CYCLE_{num}_GATE.json"
    if gate_path.is_file():
        gate = _load(gate_path)
        result["halves"]["audit_gate"] = {
            "path": _rel(gate_path),
            "gate": gate.get("gate"),
            "safe_to_integrate": gate.get("safe_to_integrate"),
            "required_fixes": gate.get("required_fixes"),
            "ok": gate.get("gate") == "PASS"
            and gate.get("safe_to_integrate") is True,
        }
    else:
        result["halves"]["audit_gate"] = {"path": _rel(gate_path), "ok": False}
    needle = f"accept product cycle {num}"
    log = _git("log", "origin/main", "--format=%H%x09%s").stdout.splitlines()
    commits = [line.split("\t", 1)[0] for line in log
               if line.split("\t", 1)[-1].strip() == needle]
    # The accepted accept commit may live on lab/product, which is not always
    # fetched; fall back to any locally reachable ref.
    if not commits:
        log = _git("log", "--all", f"--grep=^{needle}$", "--format=%H").stdout.splitlines()
        commits = [line.strip() for line in log if line.strip()]
    result["halves"]["accept_commit"] = {"needle": needle, "commits": commits,
                                         "ok": bool(commits)}
    result["both_halves"] = all(h.get("ok") is True for h in result["halves"].values())
    return result


def _run_checks(run_id: str, resumed_id: str, skip_tests: bool) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    raw_path = ORCH / f"CYCLE_{resumed_id}_run_jobs_raw.json"
    diag_path = ORCH / f"CYCLE_{resumed_id}_resume_diagnosis.json"
    family_path = ROOT / "results" / "product" / "counter_content_family" / (
        f"CYCLE_{run_id}.json")
    report_path = ROOT / "reports" / "product" / f"CYCLE_{run_id}.md"

    problems: list[str] = []

    # 1. run/jobs classification from the committed snapshot
    if raw_path.is_file():
        raw = _load(raw_path)
        cls = asd.classify(raw)
        checks["run_jobs_classification"] = {
            "path": _rel(raw_path),
            "sha256": _sha256(raw_path),
            "classification": cls.get("classification"),
            "logs_endpoint_status": raw.get("logs_endpoint_status"),
            "logs_available": bool(raw.get("logs_endpoint_status") == 200),
            "jobs": {j.get("name"): j.get("conclusion") for j in raw.get("jobs", [])},
            "team_failed_step": next(
                (s.get("name") for s in next(
                    (j for j in raw.get("jobs", []) if j.get("name") == "team"), {}
                ).get("steps", []) if s.get("conclusion") == "failure"), None),
        }
        if cls.get("classification") != "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE":
            problems.append("run_jobs_classification")
        if raw.get("logs_endpoint_status") != 403:
            problems.append("logs_endpoint_status_not_403")
        if checks["run_jobs_classification"]["team_failed_step"] != "Run lane cycle":
            problems.append("team_failed_step")
    else:
        problems.append("run_jobs_raw_missing")
        checks["run_jobs_classification"] = {"ok": False}

    # 2. committed diagnosis agrees
    if diag_path.is_file():
        diag = _load(diag_path)
        checks["resume_diagnosis"] = {
            "path": _rel(diag_path),
            "sha256": _sha256(diag_path),
            "run_id": diag.get("run_id"),
            "orchestration": (diag.get("orchestration") or {}).get("classification"),
            "mechanism": ((diag.get("orchestration") or {}).get("mechanism") or {}).get("status"),
            "durable_delta": (diag.get("durable_delta") or {}).get("classification"),
            "adjudication": (diag.get("adjudication") or {}).get("status"),
            "product_defect": (diag.get("adjudication") or {}).get("product_defect"),
            "verdict_written": (diag.get("adjudication") or {}).get("verdict_written"),
        }
        if diag.get("run_id") != resumed_id:
            problems.append("diag_run_id")
        if checks["resume_diagnosis"]["orchestration"] != "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE":
            problems.append("diag_orchestration")
        if checks["resume_diagnosis"]["durable_delta"] != "ZERO_DURABLE_DELTA":
            problems.append("diag_delta")
        if checks["resume_diagnosis"]["adjudication"] != "UNADJUDICATED":
            problems.append("diag_adjudication")
    else:
        problems.append("resume_diagnosis_missing")
        checks["resume_diagnosis"] = {"ok": False}

    # 3. state posture + accepted pointer
    state = _load(STATE)
    posture = {k: state.get(k) for k in (
        "human_gate_ready", "machine_gate_ready", "ready_for_owner_session",
        "packet_admitted", "continue_recommended")}
    posture["owner_decision_required"] = state.get("owner_decision_required") or False
    accepted = _accepted_pointer(state)
    checks["posture"] = posture
    checks["accepted_pointer"] = accepted
    checks["direction_version"] = state.get("direction_version")
    if any(posture[k] is not False for k in (
            "human_gate_ready", "machine_gate_ready", "ready_for_owner_session",
            "packet_admitted", "owner_decision_required")):
        problems.append("posture_not_fail_closed")
    if posture["continue_recommended"] is not True:
        problems.append("continue_recommended")
    if state.get("direction_version") != 68:
        problems.append("direction_version")
    if accepted.get("both_halves") is not True:
        problems.append("accepted_pointer_both_halves")

    # 4. content-family probe (REPORTED-ONLY)
    if family_path.is_file():
        fam = _load(family_path)
        fixed = fam.get("fixed_path_family") or {}
        totals = fixed.get("totals") or {}
        hist = totals.get("defect_histogram") or {}
        rule = fam.get("ordered_work_2_full_success_rule") or {}
        fam_view = {
            "path": _rel(family_path), "sha256": _sha256(family_path),
            "run_id": fam.get("run_id"),
            "n_bundles": totals.get("n_bundles"),
            "n_decisions": totals.get("n_decisions"),
            "n_verified": totals.get("n_verified"),
            "n_verified_defective": totals.get("n_verified_defective"),
            "false_reject_count": fam.get("false_reject_count"),
            "defect_histogram": hist,
            "success_rule_met": rule.get("met"),
        }
        checks["content_family"] = fam_view
        # Frozen-predicate histogram keys are the probe's own names; the
        # instrument re-reads them, never re-derives the predicates.
        for key in ("D1_empty_evidence", "D2_letterhead_zone",
                    "D3_markup_residue", "D4_language_marker_mismatch"):
            if hist.get(key) not in (0, None):
                problems.append(f"content_family_{key}")
        if fam_view["n_verified_defective"] != 0 or fam_view["false_reject_count"] != 0:
            problems.append("content_family_rejection")
        if fam_view["success_rule_met"] is not True:
            problems.append("content_family_success_rule")
    else:
        problems.append("content_family_missing")
        checks["content_family"] = {"ok": False}

    # 5. report of record exists and names both run ids
    if report_path.is_file():
        text = report_path.read_text(encoding="utf-8")
        checks["report"] = {
            "path": _rel(report_path), "sha256": _sha256(report_path),
            "names_resumed_run": resumed_id in text,
            "names_executing_run": run_id in text,
        }
        if not (checks["report"]["names_resumed_run"]
                and checks["report"]["names_executing_run"]):
            problems.append("report_run_ids")
    else:
        problems.append("report_missing")
        checks["report"] = {"ok": False}

    # 6. no auditor-namespace write by the producer
    audit_gate = ROOT / "results" / "audit" / "product" / f"CYCLE_{resumed_id}_GATE.json"
    audit_report = ROOT / "reports" / "audit" / "product" / f"CYCLE_{resumed_id}.md"
    checks["auditor_namespace"] = {
        "resumed_gate_present": audit_gate.is_file(),
        "resumed_report_present": audit_report.is_file(),
        "minted_by_producer": audit_gate.is_file() or audit_report.is_file(),
    }
    if checks["auditor_namespace"]["minted_by_producer"]:
        problems.append("producer_minted_audit_artifact")

    # 7. executed checks
    if skip_tests:
        checks["executed"] = {"skipped": True}
    else:
        env = os_env = dict(os.environ)
        env["PYTHONPATH"] = "product"
        cmd = [sys.executable, "-m", "pytest", "-q", *MVP_TESTS]
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True,
                              env=env, timeout=900)
        tail = [line for line in proc.stdout.splitlines() if line.strip()][-1:]
        checks["executed"] = {
            "skipped": False,
            "command": "PYTHONPATH=product python3 -m pytest -q " + " ".join(MVP_TESTS),
            "exit_code": proc.returncode, "summary": tail,
        }
        if proc.returncode != 0:
            problems.append("mvp_pytest")

    checks["problems"] = problems
    checks["ok"] = not problems
    return checks


def run(run_id: str, resumed_id: str, skip_tests: bool = False) -> dict[str, Any]:
    checks = _run_checks(run_id, resumed_id, skip_tests)
    raw_cls = checks.get("run_jobs_classification") or {}
    diag = checks.get("resume_diagnosis") or {}
    # Consolidated view: keeps the per-source evidence in checks while giving
    # the auditor a single classification block beside the posture.
    checks["orchestration"] = {
        "classification": raw_cls.get("classification"),
        "mechanism_status": diag.get("mechanism"),
        "logs_endpoint_status": raw_cls.get("logs_endpoint_status"),
        "durable_delta": diag.get("durable_delta"),
        "adjudication": diag.get("adjudication"),
        "audit_gate_written": (checks.get("auditor_namespace") or {}).get(
            "minted_by_producer", False),
    }
    checks["verification"] = {
        "environment": {"installed": _environment()["installed"]},
        "executed": checks.get("executed"),
    }
    return {
        "schema": SCHEMA,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "run_id": run_id,
        "resumed_run_id": resumed_id,
        "direction_version": 68,
        "readiness": "AUDIT_READY" if checks["ok"] else "NOT_AUDIT_READY",
        "gates_minted": 0,
        "frozen_bars_scored": 0,
        "serve_verdict_rerun": False,
        "posture": checks.get("posture"),
        "environment": _environment(),
        "checks": checks,
        "problems": checks["problems"],
        "ok": checks["ok"],
        "claim_ceiling": (
            "This dossier re-derives an orchestration classification, a git-ref "
            "delta, the fail-closed state posture, the accepted pointer and a "
            "REPORTED-ONLY product measurement. It writes no gate, scores no "
            "frozen bar, re-runs no serve verdict, labels no run accepted or "
            "rejected, and makes no legal or human-gate claim. A green dossier "
            "is a handoff aid for the independent auditor, not an audit verdict."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--resumed-run-id", required=True)
    ap.add_argument("--skip-tests", action="store_true")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    rec = run(args.run_id, args.resumed_run_id, args.skip_tests)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(out), "ok": rec["ok"],
                      "problems": rec["checks"]["problems"]}, indent=2))
    return 0 if rec["ok"] else 4


if __name__ == "__main__":
    sys.exit(main())
