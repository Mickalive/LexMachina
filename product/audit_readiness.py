#!/usr/bin/env python3
"""Bounded audit-readiness dossier for a resumed product snapshot.

Why this exists
---------------
Run 40196023042's producer finished cleanly and persisted a real delta, but its
independent audit died at ``LEX_WORK_QUANTUM_EXPIRED seconds=2700`` (exit 78)
before writing a gate.  The next auditor should not have to spend its own
quantum rediscovering the slice, the accepted pointer or which artifacts are
claim-bearing.  This module gives it one command that re-derives the snapshot's
claims on bounded inputs and records the exact evidence.

What it does
------------
* runs the product-owned state contract;
* checks the fail-closed posture and the accepted pointer;
* re-classifies the resumed run from its committed run/jobs snapshot;
* verifies the resumed run's committed diagnosis (quantum expiry, durable
  delta, unadjudicated status);
* hashes and structurally checks the claim-bearing artifacts (including the
  before/after bytes for the v68 rejection/incumbent leg);
* re-runs the shipped progressive query smoke over a real socket in fixture
  mode (no network, no paid inference);
* runs the bounded MVP core pytest set;
* confirms the producer wrote no auditor-namespace path and minted no gate.

It deliberately does NOT write ``results/audit/**``, mint a gate, score a
frozen bar, re-run a serve verdict, or label any run accepted/rejected.  Its
output is a dossier for the independent auditor, never a verdict.

Usage
-----
    python3 product/audit_readiness.py --run-id 40200882831 \\
        --out results/product/audit_readiness/CYCLE_40200882831_audit_readiness.json

    # fast mode while iterating (skip the two slow re-runs):
    python3 product/audit_readiness.py --run-id X --skip-tests --skip-smoke --out /tmp/x.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "product-audit-readiness/1"
DIRECTION_VERSION = 68
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from product.state_contract import accepted_pointer_evidence  # noqa: E402

ORCH = ROOT / "results" / "product" / "orchestration"
CONTENT_FAMILY = (ROOT / "results" / "product" / "counter_content_family"
                  / "CYCLE_40188639817.json")
# The default profile's pinned family measurement.  A newer profile may pin its
# own artifact/numbers; the report is always REPORTED-ONLY and the frozen
# predicates are never re-derived here.
CONTENT_FAMILY_EXPECTED = {
    "n_bundles": 29,
    "n_decisions": 2900,
    "n_verified": 20,
    "n_verified_defective": 0,
    "false_reject_count": 0,
}
BEFORE_BUNDLE = (ROOT / "results" / "product" / "offline_slice"
                 / "20261024T142517Z" / "rent-default.bundle.json")
AFTER_BUNDLE = (ROOT / "results" / "product" / "offline_slice"
                / "20261025T070356Z" / "rent-default.bundle.json")
STATE = ROOT / "state" / "product.json"

# --- run profiles -------------------------------------------------------
# The dossier was originally pinned to one snapshot (40196023042, resumed by
# 40200882831).  Every later operational resume needs the same bounded
# dossier, so the run-specific facts live in profiles instead of being
# re-derived per cycle.  A profile is selected by the --run-id argument
# (either the resuming run or the resumed snapshot) and falls back to
# ``DEFAULT_PROFILE_KEY`` so the original pinned behaviour is unchanged.
# Everything a profile does NOT override (posture, accepted pointer, frozen
# claim artifacts, MVP test set) is shared by design: those are accepted
# evidence, not per-run facts.
RESUMED_RUN_ID = "40196023042"          # default profile (kept for imports)
PREDECESSOR_RUN_ID = "40193974025"      # default profile (kept for imports)
RAW = ORCH / f"CYCLE_{RESUMED_RUN_ID}_run_jobs_raw.json"
RESUME_DIAG = ORCH / f"CYCLE_{RESUMED_RUN_ID}_resume_diagnosis.json"
INHERITED_REPORT = ROOT / "reports" / "product" / f"CYCLE_{PREDECESSOR_RUN_ID}.md"
CURRENT_REPORT = ROOT / "reports" / "product" / "CYCLE_40200882831.md"
DEFAULT_PROFILE_KEY = "40196023042"

PROFILES: dict[str, dict[str, Any]] = {
    "40196023042": {
        "resumed_run_id": "40196023042",
        "predecessor_run_id": "40193974025",
        "raw": ORCH / "CYCLE_40196023042_run_jobs_raw.json",
        "resume_diag": ORCH / "CYCLE_40196023042_resume_diagnosis.json",
        "inherited_report": ROOT / "reports" / "product"
                            / "CYCLE_40193974025.md",
        "current_report": ROOT / "reports" / "product" / "CYCLE_40200882831.md",
        "classification": "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE",
        "failed_job": "audit",
        "quantum_seconds": 2700,
        "exit_code": 78,
        "changed_files": 9,
        "changed_paths_include": ("product/audit_step_diagnosis.py",),
        "cycle_test": "product/tests/test_cycle_40200882831.py",
        "state_block": "cycle_40200882831_operational_resume",
    },
    "40200882831": {"alias_of": "40196023042"},
    "40217792931": {
        "resumed_run_id": "40217792931",
        "predecessor_run_id": "40211497166",
        "raw": ORCH / "CYCLE_40217792931_run_jobs_raw.json",
        "resume_diag": ORCH / "CYCLE_40217792931_resume_diagnosis.json",
        "inherited_report": None,
        "current_report": ROOT / "reports" / "product"
                          / "CYCLE_40217792931.md",
        "classification": "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE",
        "failed_job": "team",
        "quantum_seconds": 2700,
        "exit_code": 78,
        "changed_files": 15,
        "changed_paths_include": ("results/product/offline_slice",),
        "cycle_test": "product/tests/test_cycle_40217792931.py",
        "state_block": "cycle_40217792931_operational_resume",
    },
    "40221519475": {"alias_of": "40217792931"},
    "40234815780": {
        "resumed_run_id": "40234815780",
        "predecessor_run_id": "40230559317",
        "raw": ORCH / "CYCLE_40234815780_run_jobs_raw.json",
        "resume_diag": ORCH / "CYCLE_40234815780_resume_diagnosis.json",
        "inherited_report": ROOT / "reports" / "product"
                            / "CYCLE_40230559317.md",
        "current_report": ROOT / "reports" / "product"
                          / "CYCLE_40234815780.md",
        "classification": "TEAM_JOB_LANE_CYCLE_STEP_FAILED_NO_GATE",
        "failed_job": "team",
        "quantum_seconds": 2700,
        "exit_code": 78,
        "changed_files": 8,
        "changed_paths_include": (
            "product/tests/test_counter_content_rejection_v68.py",
            "results/product/repair_40234815780/",
        ),
        "cycle_test": "product/tests/test_cycle_40234815780_resume.py",
        "state_block": "cycle_40234815780_operational_resume",
        # This resume's family artifact is newer than the default profile's.
        # Both are valid REPORTED-ONLY measurements; the profile pins the one
        # the current run's audit should consume, not a re-derived number.
        "content_family": ROOT / "results" / "product" / "counter_content_family"
                          / "CYCLE_40230559317.json",
        "content_family_expected": {
            "n_bundles": 43,
            "n_decisions": 4300,
            "n_verified": 44,
            "n_verified_defective": 0,
            "false_reject_count": 0,
        },
    },
}

# Active profile; empty means "the module constants above" (the original
# pinned run).  Set by run()/select_profile() only.
PROFILE: dict[str, Any] = {}


def select_profile(run_id: str) -> dict[str, Any]:
    """Resolve the dossier profile for ``run_id`` (aliases are followed).

    A dossier for the wrong run is worse than no dossier: it would re-derive
    another run's claims and label them with this run's id.  Unknown run ids
    therefore fail closed instead of silently inheriting the default profile.
    """
    key = str(run_id)
    prof = PROFILES.get(key)
    while isinstance(prof, dict) and "alias_of" in prof:
        prof = PROFILES.get(str(prof["alias_of"]))
    if prof is None:
        raise SystemExit(
            f"no audit-readiness profile for run {key}; refusing to fall back "
            f"to {DEFAULT_PROFILE_KEY} and publish another run's claims")
    return dict(prof)


def p(field: str, default: Any = None) -> Any:
    """Profile field with a fallback to the pinned module constants."""
    if field in PROFILE:
        return PROFILE[field]
    return default


def _report_paths() -> list[Path]:
    out = []
    for value in (p("inherited_report", INHERITED_REPORT),
                  p("current_report", CURRENT_REPORT)):
        if value is not None:
            out.append(Path(value))
    return out

MVP_CORE_TESTS = (
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

STATE_TIMEOUT_S = 180
SMOKE_TIMEOUT_S = 240
PYTEST_TIMEOUT_S = 600
D2_DECISION = "gr_gerichte_ERZ 2010 25"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _run(cmd: list[str], timeout: int) -> dict[str, Any]:
    started = time.monotonic()
    try:
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True,
                              text=True, timeout=timeout, check=False)
        return {
            "command": " ".join(cmd),
            "exit_code": proc.returncode,
            "seconds": round(time.monotonic() - started, 3),
            "stdout_tail": proc.stdout[-4000:],
            "stderr_tail": proc.stderr[-4000:],
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": " ".join(cmd),
            "exit_code": None,
            "seconds": round(time.monotonic() - started, 3),
            "stdout_tail": (exc.stdout or b"").decode("utf-8", "replace")[-4000:]
            if isinstance(exc.stdout, bytes) else (exc.stdout or "")[-4000:],
            "stderr_tail": (exc.stderr or b"").decode("utf-8", "replace")[-4000:]
            if isinstance(exc.stderr, bytes) else (exc.stderr or "")[-4000:],
            "timed_out": True,
        }


def _check(check_id: str, title: str, ok: bool, detail: Any,
           evidence: list[str] | None = None,
           command: str | None = None, seconds: float | None = None,
           mandatory: bool = True) -> dict[str, Any]:
    return {
        "id": check_id,
        "title": title,
        "status": "PASS" if ok else "FAIL",
        "mandatory": mandatory,
        "detail": detail,
        "evidence": evidence or [],
        "command": command,
        "seconds": seconds,
    }


def _skip(check_id: str, title: str, reason: str,
          mandatory: bool = False) -> dict[str, Any]:
    return {
        "id": check_id,
        "title": title,
        "status": "SKIP",
        "mandatory": mandatory,
        "detail": reason,
        "evidence": [],
        "command": None,
        "seconds": None,
    }


def check_state_contract() -> dict[str, Any]:
    cmd = [sys.executable, "product/state_contract.py", "--check",
           "--direction-version", str(DIRECTION_VERSION), "--json"]
    started = time.monotonic()
    try:
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True,
                              text=True, timeout=STATE_TIMEOUT_S, check=False)
        exit_code, stdout, stderr = proc.returncode, proc.stdout, proc.stderr
        timed_out = False
    except subprocess.TimeoutExpired as exc:  # pragma: no cover - defensive
        exit_code = None
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        timed_out = True
    seconds = round(time.monotonic() - started, 3)
    report: dict[str, Any] = {}
    if stdout.strip():
        try:
            report = json.loads(stdout)
        except json.JSONDecodeError:
            report = {}
    ok = exit_code == 0 and bool(report.get("ok"))
    detail = {
        "timed_out": timed_out,
        "stderr_tail": stderr[-1000:],
        "workflow_validation": report.get("workflow_validation"),
        "write_scope": report.get("write_scope"),
        "audit_artifact_ownership": {
            "ok": (report.get("audit_artifact_ownership") or {}).get("ok"),
            "producer_wrote_audit_paths": (
                report.get("audit_artifact_ownership") or {}
            ).get("producer_wrote_audit_paths"),
        },
        "shadow_state": report.get("shadow_state"),
    }
    return _check("state_contract",
                  "Canonical state satisfies the workflow contract and lane scope",
                  ok, detail, ["state/product.json", "product/state_contract.py"],
                  " ".join(cmd), seconds)


def check_posture() -> dict[str, Any]:
    st = _load(STATE)
    expected = {
        "lane": "product",
        "direction_version": DIRECTION_VERSION,
        "continue_recommended": True,
        "human_gate_ready": False,
        "machine_gate_ready": False,
        "packet_admitted": False,
        "ready_for_owner_session": False,
    }
    bad = {k: {"expected": v, "actual": st.get(k)}
           for k, v in expected.items() if st.get(k) != v}
    pointer = accepted_pointer_evidence(st, ROOT)
    ok = not bad and not pointer["problems"]
    return _check(
        "posture",
        "Fail-closed posture and an accepted pointer that still satisfies "
        "both halves of requirement 4",
        ok,
        {"mismatches": bad, "accepted_pointer": pointer},
        ["state/product.json"],
    )


def check_resumed_diagnosis() -> dict[str, Any]:
    raw = Path(p("raw", RAW))
    resume_diag = Path(p("resume_diag", RESUME_DIAG))
    resumed_id = p("resumed_run_id", RESUMED_RUN_ID)
    predecessor = p("predecessor_run_id", PREDECESSOR_RUN_ID)
    classification = p("classification", "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE")
    failed_job = p("failed_job", "audit")
    quantum_seconds = p("quantum_seconds", 2700)
    exit_code = p("exit_code", 78)
    changed_files = p("changed_files", 9)
    diag = _load(resume_diag)
    orch = diag.get("orchestration") or {}
    delta = diag.get("durable_delta") or {}
    adj = diag.get("adjudication") or {}
    mechanism = orch.get("mechanism") or {}
    problems = []
    if diag.get("run_id") != resumed_id:
        problems.append("run_id")
    if diag.get("predecessor_run_id") != predecessor:
        problems.append("predecessor_run_id")
    if orch.get("classification") != classification:
        problems.append("classification")
    if mechanism.get("status") != "OBSERVED_QUANTUM_EXPIRED":
        problems.append("mechanism_status")
    if mechanism.get("quantum_expired") is not True:
        problems.append("quantum_expired")
    if mechanism.get("quantum_seconds") != quantum_seconds:
        problems.append("quantum_seconds")
    if mechanism.get("exit_code") != exit_code:
        problems.append("exit_code")
    if (orch.get("audit") or {}).get("gate_file_written") is not False:
        problems.append("gate_file_written")
    if delta.get("classification") != "COMMITTED_DELTA":
        problems.append("durable_delta")
    if delta.get("changed_files") != changed_files:
        problems.append("changed_files")
    paths_sample = delta.get("changed_paths_sample") or []
    for needle in p("changed_paths_include", ()):
        if not any(str(needle) in str(s) for s in paths_sample):
            problems.append(f"changed_paths_include:{needle}")
    if adj.get("status") != "UNADJUDICATED" or adj.get("accepted") is not False:
        problems.append("adjudication")
    who = ("independent-audit" if failed_job == "audit"
           else "lane-cycle (producer)")
    return _check(
        "resumed_diagnosis",
        f"Resumed run {resumed_id}: {who} work-quantum expiry observed, "
        "durable delta present, run unadjudicated",
        not problems,
        {"problems": problems, "failed_job": failed_job,
         "audit_step_seconds": (
             (orch.get("audit") or {}).get("independent_audit_step_seconds")),
         "failed_step_seconds": ((orch.get("team") or {}).get(
             "failed_step_seconds")),
         "changed_files": delta.get("changed_files"),
         "changed_paths_sample": paths_sample},
        [str(raw.relative_to(ROOT)), str(resume_diag.relative_to(ROOT))],
    )


def _row(bundle: dict, decision_id: str) -> dict | None:
    return next((r for r in bundle.get("decisions") or []
                 if r.get("decision_id") == decision_id), None)


def check_claim_artifacts() -> dict[str, Any]:
    cf_path = Path(p("content_family", CONTENT_FAMILY))
    expected = dict(p("content_family_expected", CONTENT_FAMILY_EXPECTED))
    paths = [
        cf_path, BEFORE_BUNDLE, AFTER_BUNDLE,
        Path(p("raw", RAW)), Path(p("resume_diag", RESUME_DIAG)),
        *_report_paths(), STATE,
    ]
    missing = [str(p.relative_to(ROOT)) for p in paths if not p.is_file()]
    hashes = {str(p.relative_to(ROOT)): _sha256(p)
              for p in paths if p.is_file()}
    problems: list[str] = []
    detail: dict[str, Any] = {}

    if not problems and cf_path.is_file():
        cf = _load(cf_path)
        fp = (cf.get("fixed_path_family") or {}).get("totals") or {}
        try:
            for key in ("n_bundles", "n_decisions", "n_verified",
                        "n_verified_defective"):
                if fp.get(key) != expected[key]:
                    problems.append(f"fixed_path_family.{key}")
            if any(v != 0 for v in (fp.get("defect_histogram") or {}).values()):
                problems.append("fixed_path_family.defect_histogram")
            if cf.get("false_reject_count") != expected["false_reject_count"]:
                problems.append("false_reject_count")
            if not (cf.get("confirmed_set") or {}).get("still_verified"):
                problems.append("confirmed_sound_row")
            if not (cf.get("ordered_work_2_success_rule") or {}).get("met"):
                problems.append("ordered_work_2_success_rule")
            if not (cf.get("ordered_work_2_full_success_rule") or {}).get("met"):
                problems.append("ordered_work_2_full_success_rule")
            if any((cf.get("frozen_predicate_provenance") or {}).get(k) is None
                   for k in ("predicate_source_sha256", "frozen_hypothesis_sha256")):
                problems.append("frozen_predicate_provenance")
        except (TypeError, AttributeError, KeyError):
            problems.append("content_family_shape")
        detail["content_family"] = {
            "path": str(cf_path.relative_to(ROOT)),
            "expected": expected,
            "n_bundles": fp.get("n_bundles"),
            "n_decisions": fp.get("n_decisions"),
            "n_verified": fp.get("n_verified"),
            "n_verified_defective": fp.get("n_verified_defective"),
            "defect_histogram": fp.get("defect_histogram"),
            "false_reject_count": cf.get("false_reject_count"),
        }

    before = after = None
    if BEFORE_BUNDLE.is_file() and AFTER_BUNDLE.is_file():
        before = _row(_load(BEFORE_BUNDLE), D2_DECISION)
        after = _row(_load(AFTER_BUNDLE), D2_DECISION)
        if before is None:
            problems.append("before_row_missing")
        elif before.get("counter_evidence_verified") is not True:
            problems.append("before_row_not_verified")
        if after is None:
            problems.append("after_row_missing")
        else:
            if after.get("counter_evidence_verified") is not False:
                problems.append("after_row_still_verified")
            if after.get("counter_evidence_unevidenced_reason") != "pivot_absent":
                problems.append("after_row_reason")
        detail["d2_before_after"] = {
            "decision_id": D2_DECISION,
            "before_verified": (before or {}).get("counter_evidence_verified"),
            "after_verified": (after or {}).get("counter_evidence_verified"),
            "after_reason": (after or {}).get("counter_evidence_unevidenced_reason"),
        }
        for path, bundle in ((BEFORE_BUNDLE, before), (AFTER_BUNDLE, after)):
            prov = ((_load(path).get("provenance") or {})
                    .get("counter_evidence_span") or {})
            if prov.get("applied") is not True:
                problems.append(f"{path.name}.span_not_applied")
            if prov.get("n_selected") != 0:
                problems.append(f"{path.name}.n_selected")

    return _check(
        "claim_artifacts",
        "Claim-bearing artifacts exist, hash, and re-derive the v68 "
        "before/after D2 rejection",
        not missing and not problems,
        {"missing": missing, "problems": problems, **detail,
         "sha256": hashes},
        [str(p.relative_to(ROOT)) for p in paths],
    )


def check_progressive_smoke(run_id: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="lex_audit_smoke_") as td:
        out = Path(td) / "smoke.json"
        cmd = [sys.executable, "product/progressive_smoke.py",
               "--run-id", run_id, "--out", str(out)]
        run = _run(cmd, SMOKE_TIMEOUT_S)
        if not out.is_file():
            return _check("progressive_smoke",
                          "Shipped progressive API answers over a real socket",
                          False, {"run": run}, [], run["command"],
                          run["seconds"])
        art = _load(out)
    by_name = {c["check"]: c for c in art.get("checks") or []}
    problems = []
    if art.get("verdict") != "PASS":
        problems.append("verdict")
    if art.get("checks_passed") != art.get("checks_total"):
        problems.append("checks")
    if (by_name.get("start_first_page_nonempty") or {}).get("detail", 0) < 100:
        problems.append("first_page")
    if (by_name.get("start_has_clusters") or {}).get("detail", 0) < 5:
        problems.append("clusters")
    if (by_name.get("start_points_have_xy") or {}).get("detail") != "100/100":
        problems.append("coordinates")
    if (by_name.get("answer_has_citations") or {}).get("detail", 0) < 1:
        problems.append("citations")
    t = art.get("timings_s") or {}
    if t.get("server_boot_s", 99) >= 3.0:
        problems.append("server_boot_budget")
    if t.get("start_s", 99) >= 1.0:
        problems.append("cached_start_budget")
    return _check(
        "progressive_smoke",
        "Shipped progressive API answers over a real socket (fixture mode)",
        not problems,
        {"problems": problems, "verdict": art.get("verdict"),
         "checks": f"{art.get('checks_passed')}/{art.get('checks_total')}",
         "timings_s": t, "mode": art.get("mode")},
        [], run["command"], run["seconds"],
    )


_PASSED_RE = re.compile(r"(\d+) passed")
_FAILED_RE = re.compile(r"(\d+) failed")
_SKIPPED_RE = re.compile(r"(\d+) skipped")
_ERROR_RE = re.compile(r"(\d+) error")


def check_mvp_tests() -> dict[str, Any]:
    cmd = [sys.executable, "-m", "pytest", *MVP_CORE_TESTS, "-q",
           "--maxfail=1"]
    run = _run(cmd, PYTEST_TIMEOUT_S)
    text = run["stdout_tail"] + "\n" + run["stderr_tail"]
    passed = int((_PASSED_RE.search(text) or [0, 0])[1] or 0)
    failed = int((_FAILED_RE.search(text) or [0, 0])[1] or 0)
    errors = int((_ERROR_RE.search(text) or [0, 0])[1] or 0)
    skipped = int((_SKIPPED_RE.search(text) or [0, 0])[1] or 0)
    ok = run["exit_code"] == 0 and passed > 0 and failed == 0 and errors == 0
    return _check(
        "mvp_core_tests",
        "Bounded MVP core pytest set is green",
        ok,
        {"passed": passed, "failed": failed, "errors": errors,
         "skipped": skipped, "timed_out": run["timed_out"],
         "files": list(MVP_CORE_TESTS)},
        [], run["command"], run["seconds"],
    )


def check_audit_namespace(run_id: str) -> dict[str, Any]:
    gate = ROOT / "results" / "audit" / "product" / f"CYCLE_{run_id}_GATE.json"
    report = (ROOT / "reports" / "audit" / "product"
              / f"CYCLE_{run_id}.md")
    pending = subprocess.run(
        ["git", "status", "--porcelain", "-uall"], cwd=str(ROOT),
        capture_output=True, text=True, check=False,
    ).stdout.splitlines()
    producer_audit = [line[3:] for line in pending
                      if line[3:].startswith(("results/audit/product/",
                                              "reports/audit/product/"))]
    ok = not gate.exists() and not report.exists() and not producer_audit
    return _check(
        "audit_namespace",
        "Producer wrote no auditor-namespace path and minted no gate",
        ok,
        {"gate_exists": gate.exists(), "report_exists": report.exists(),
         "pending_audit_paths": producer_audit},
        [str(gate.relative_to(ROOT)), str(report.relative_to(ROOT))],
    )


def run(run_id: str, direction_version: int = DIRECTION_VERSION,
        include_tests: bool = True, include_smoke: bool = True) -> dict[str, Any]:
    if direction_version != DIRECTION_VERSION:
        raise SystemExit(
            f"this snapshot was dispatched under direction v{DIRECTION_VERSION}; "
            f"got v{direction_version}"
        )
    PROFILE.clear()
    PROFILE.update(select_profile(run_id))
    resume_diag = Path(p("resume_diag", RESUME_DIAG))
    raw = Path(p("raw", RAW))
    resumed_id = p("resumed_run_id", RESUMED_RUN_ID)
    predecessor = p("predecessor_run_id", PREDECESSOR_RUN_ID)
    failed_job = p("failed_job", "audit")
    resumed = _load(resume_diag)
    checks = [
        check_state_contract(),
        check_posture(),
        check_resumed_diagnosis(),
        check_claim_artifacts(),
        check_audit_namespace(run_id),
    ]
    if include_smoke:
        checks.append(check_progressive_smoke(run_id))
    else:
        checks.append(_skip("progressive_smoke",
                            "Shipped progressive API answers over a real socket",
                            "skipped by --skip-smoke"))
    if include_tests:
        checks.append(check_mvp_tests())
    else:
        checks.append(_skip("mvp_core_tests",
                            "Bounded MVP core pytest set is green",
                            "skipped by --skip-tests"))

    failed = [c["id"] for c in checks if c["status"] == "FAIL"]
    skipped = [c["id"] for c in checks if c["status"] == "SKIP"]
    overall = "FAIL" if failed else ("PASS" if not skipped else "PARTIAL")
    who = ("audit" if failed_job == "audit" else "team lane-cycle")
    inherited = p("inherited_report", INHERITED_REPORT)
    cycle_test = p("cycle_test", "product/tests/test_cycle_40200882831.py")
    delta_files = ((resumed.get("durable_delta") or {}).get("changed_files"))
    cf_path = Path(p("content_family", CONTENT_FAMILY))
    cf_expected = dict(p("content_family_expected", CONTENT_FAMILY_EXPECTED))
    live_state = _load(STATE)
    return {
        "schema": SCHEMA,
        "generated_at": _now(),
        "run_id": str(run_id),
        "resumed_run_id": resumed_id,
        "predecessor_run_id": predecessor,
        "profile": "default" if resumed_id == RESUMED_RUN_ID else resumed_id,
        "direction_version": DIRECTION_VERSION,
        "overall_status": overall,
        "failed_checks": failed,
        "skipped_checks": skipped,
        "checks": checks,
        "resumed_run": {
            "classification": (resumed.get("orchestration") or {}).get(
                "classification"),
            "mechanism": ((resumed.get("orchestration") or {}).get("mechanism")
                          or {}).get("status"),
            "quantum_seconds": p("quantum_seconds", 2700),
            "exit_code": p("exit_code", 78),
            "failed_job": failed_job,
            "durable_delta": (resumed.get("durable_delta") or {}).get(
                "classification"),
            "adjudication": (resumed.get("adjudication") or {}).get("status"),
        },
        "claims": [
            {"id": "C1",
             "claim": f"Run {resumed_id}'s {who} agent ended on the workflow "
                      f"work quantum ({p('quantum_seconds', 2700)} s, exit "
                      f"{p('exit_code', 78)}) before an independent gate could "
                      "be written; observed from the public check-run "
                      "annotations, not inferred.",
             "check": "resumed_diagnosis",
             "artifacts": [str(raw.relative_to(ROOT)),
                           str(resume_diag.relative_to(ROOT))]},
            {"id": "C2",
             "claim": f"Run {resumed_id} persisted an {delta_files}-file "
                      f"durable delta over {predecessor} and is UNADJUDICATED.",
             "check": "resumed_diagnosis",
             "artifacts": [str(resume_diag.relative_to(ROOT))]},
            {"id": "C3",
             "claim": "The v68 rejection/incumbent leg flips the D2 letterhead "
                      "row from verified to unverified with reason pivot_absent.",
             "check": "claim_artifacts",
             "artifacts": [str(BEFORE_BUNDLE.relative_to(ROOT)),
                           str(AFTER_BUNDLE.relative_to(ROOT)),
                           str(cf_path.relative_to(ROOT))]},
            {"id": "C4",
             "claim": f"The fixed-path family is {cf_expected['n_bundles']} "
                      f"bundles / {cf_expected['n_decisions']} decisions / "
                      f"{cf_expected['n_verified']} verified rows / "
                      f"{cf_expected['n_verified_defective']} "
                      "verified-and-defective, with the sound row retained "
                      "and 0 false rejects (REPORTED-ONLY measurement).",
             "check": "claim_artifacts",
             "artifacts": [str(cf_path.relative_to(ROOT))]},
            {"id": "C5",
             "claim": "The shipped progressive query slice still answers over a "
                      "real socket in fixture mode within the local budgets.",
             "check": "progressive_smoke",
             "artifacts": ["re-run to a temp path (no repository mutation)"]},
            {"id": "C6",
             "claim": "The bounded MVP core pytest set is green.",
             "check": "mvp_core_tests", "artifacts": list(MVP_CORE_TESTS)},
            {"id": "C7",
             "claim": "Posture is fail-closed and the accepted pointer "
                      f"({live_state.get('accepted_run_id')} / "
                      f"{str(live_state.get('accepted_commit') or '')[:9]}) "
                      "satisfies BOTH halves of requirement 4: a committed "
                      "PASS/safe gate and an accept commit.",
             "check": "posture", "artifacts": ["state/product.json"]},
            {"id": "C8",
             "claim": "This run minted no audit gate and wrote no "
                      "auditor-namespace path.",
             "check": "audit_namespace", "artifacts": []},
        ],
        "audit_entry_points": {
            "one_command": (
                "python3 product/audit_readiness.py --run-id "
                f"{run_id} --out /tmp/lex_audit_readiness.json"
            ),
            "resumed_run_diagnosis": str(resume_diag.relative_to(ROOT)),
            "inherited_report": (str(Path(inherited).relative_to(ROOT))
                                 if inherited else None),
            "current_report": str(Path(
                p("current_report", CURRENT_REPORT)).relative_to(ROOT)),
            "current_cycle_test": f"python3 -m pytest {cycle_test} -q",
            "not_required": (
                "Do not re-derive accepted evaluation 40070818687 / "
                "40068038783 / 40105794124 or the D2 profile 40089391202; "
                "they are consumed findings cited by the lane. Historical "
                "cycle tests that assert predecessor git refs are not part of "
                "this snapshot's claim set and may report REF_ABSENT in the "
                "audit worktree, which fetches only the accepted base and the "
                "current team ref."
            ),
        },
        "posture": {
            "audit_write_scope": "producer wrote only product-owned paths",
            "gate_minted": False,
            "frozen_bar_scored": False,
            "serve_verdict_rerun": False,
            "run_label": "UNADJUDICATED",
            "human_gate_ready": False,
            "machine_gate_ready": False,
        },
        "claim_ceiling": (
            "A bounded audit-readiness dossier, not an audit. It re-derives "
            "or hashes the snapshot's published claims and records the exact "
            "commands; it writes no gate, scores no frozen bar, re-runs no "
            "serve verdict, and labels no run accepted or rejected."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--direction-version", type=int,
                    default=DIRECTION_VERSION)
    ap.add_argument("--skip-tests", action="store_true")
    ap.add_argument("--skip-smoke", action="store_true")
    args = ap.parse_args(argv)
    rec = run(args.run_id, direction_version=args.direction_version,
              include_tests=not args.skip_tests,
              include_smoke=not args.skip_smoke)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(json.dumps({
        "out": str(out),
        "overall_status": rec["overall_status"],
        "failed_checks": rec["failed_checks"],
        "skipped_checks": rec["skipped_checks"],
        "checks": {c["id"]: c["status"] for c in rec["checks"]},
    }, indent=2))
    return 0 if rec["overall_status"] in ("PASS", "PARTIAL") else 1


if __name__ == "__main__":
    raise SystemExit(main())
