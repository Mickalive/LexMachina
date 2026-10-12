#!/usr/bin/env python3
"""Deterministic cycle finisher for frontier-generative-audit (charter v2).

Why this exists
---------------
Run 38193076995 completed all substantive verification but its producer
session died *after* advancing ``state/frontier/frontier-generative-audit.json``
and *before* publishing the per-run acceptance matrix / cycle report, so the
workflow's producer step failed and the run was operationally resumed.
Publishing must not depend on a long-lived agent session: this script runs the
frozen suites, (optionally) the live probes and end-to-end examples, and emits
machine-readable acceptance evidence for a given run id.

Usage
-----
Offline deterministic finish (CI default)::

    python3 frontier/frontier-generative-audit/verify_cycle.py --run-id 38193475195

Include live free-model smoke + live OpenCaseLaw probes/e2e::

    LEX_REAL_MODEL=1 LEX_LIVE_OCL=1 \
    python3 frontier/frontier-generative-audit/verify_cycle.py --run-id 38193475195 --live

Only verify, do not write evidence files::

    python3 frontier/frontier-generative-audit/verify_cycle.py --run-id X --check-only

Outputs (team scope only)
-------------------------
* ``results/frontier/frontier-generative-audit/acceptance_matrix_run<id>.json``
  immutable per-run matrix (never overwritten by later runs);
* ``results/frontier/frontier-generative-audit/acceptance_matrix.json``
  pointer/copy for the most recent verified run;
* exit code 0 iff every executed check passed.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
CANONICAL_SUITE = (
    REPO / "tests" / "frontier" / "frontier-generative-audit" / "test_generative_audit_v2.py"
)
LEGACY_SUITE = REPO / "generative_audit" / "tests" / "test_generative_audit.py"
RUN_E2E = HERE / "run_e2e.py"
PROBE_OCL = HERE / "probe_ocl.py"
RESULTS = REPO / "results" / "frontier" / "frontier-generative-audit"

RESULTS_RE = re.compile(r"Results:\s*(\d+)\s*passed,\s*(\d+)\s*failed")


def _run(cmd: List[str], env: Dict[str, str], timeout: int) -> Tuple[int, str]:
    proc = subprocess.run(
        cmd,
        cwd=str(REPO),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout,
    )
    return proc.returncode, proc.stdout


def _parse_suite(out: str) -> Tuple[int, int]:
    matches = RESULTS_RE.findall(out)
    if not matches:
        return -1, -1
    passed = sum(int(p) for p, _ in matches)
    failed = sum(int(f) for _, f in matches)
    return passed, failed


def check_suites(live: bool) -> Dict[str, Any]:
    env = dict(os.environ)
    env.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    out: Dict[str, Any] = {}

    code, log = _run([sys.executable, str(LEGACY_SUITE)], env, timeout=900)
    p, f = _parse_suite(log)
    out["legacy_suite"] = {
        "command": f"{sys.executable} {LEGACY_SUITE}",
        "exit_code": code,
        "passed": p,
        "failed": f,
        "ok": code == 0 and f == 0 and p >= 10,
        "tail": log.strip().splitlines()[-3:],
    }

    suite_env = dict(env)
    if live:
        suite_env["LEX_REAL_MODEL"] = "1"
        suite_env["LEX_LIVE_OCL"] = "1"
    code, log = _run([sys.executable, str(CANONICAL_SUITE)], suite_env, timeout=3600)
    p, f = _parse_suite(log)
    out["canonical_suite"] = {
        "command": f"{sys.executable} {CANONICAL_SUITE}"
        + ("  [LEX_REAL_MODEL=1 LEX_LIVE_OCL=1]" if live else "  [offline]"),
        "exit_code": code,
        "passed": p,
        "failed": f,
        "ok": code == 0 and f == 0 and p >= 29,
        "live_flags": bool(live),
        "tail": log.strip().splitlines()[-6:],
    }
    return out


def check_fixture_e2e(run_id: str, check_only: bool) -> Dict[str, Any]:
    target = RESULTS / f"cached_example_fixture_run{run_id}.json"
    dest = target if not check_only else Path(tempfile.mkstemp(suffix=".json")[1])
    env = dict(os.environ)
    env.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    code, log = _run(
        [sys.executable, str(RUN_E2E), "--fixture", "--out", str(dest)],
        env,
        timeout=600,
    )
    info: Dict[str, Any] = {
        "exit_code": code,
        "out": str(dest),
        "ok": code == 0 and dest.exists(),
    }
    if dest.exists():
        data = json.loads(dest.read_text())
        bundle_ids = {
            d["decision_id"] for d in data["audited_product_bundle"]["decisions"]
        }
        unknown = [c for c in data["cited_decision_ids"] if c not in bundle_ids]
        info.update(
            {
                "cited_decision_ids": data["cited_decision_ids"],
                "unknown_cited_ids": unknown,
                "redacted_citation_ids": data["redacted_citation_ids"],
                "status_summary": data["status_summary"],
                "findings": len(data["adversarial_findings"]),
                "citation_constraint_ok": not unknown
                and not data["redacted_citation_ids"],
            }
        )
        info["ok"] = info["ok"] and info["citation_constraint_ok"]
    if check_only:
        dest.unlink(missing_ok=True)
    return info


def check_live(run_id: str, check_only: bool) -> Dict[str, Any]:
    env = dict(os.environ)
    env.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    out: Dict[str, Any] = {}

    probe_dest = (
        Path(tempfile.mkstemp(suffix=".json")[1])
        if check_only
        else RESULTS / f"ocl_live_probe_run{run_id}.json"
    )
    code, log = _run(
        [sys.executable, str(PROBE_OCL), "--out", str(probe_dest)], env, timeout=600
    )
    probe: Dict[str, Any] = {"exit_code": code, "out": str(probe_dest)}
    if probe_dest.exists():
        data = json.loads(probe_dest.read_text())
        probe["live_host_reachable"] = data.get("live_host_reachable")
        probe["routes"] = data.get("routes") or {
            k: v.get("http") for k, v in (data.get("results") or {}).items()
        }
        probe["ok"] = code == 0 and bool(data.get("live_host_reachable"))
    else:
        probe["ok"] = False
    if check_only:
        probe_dest.unlink(missing_ok=True)
    out["ocl_probe"] = probe

    model = os.environ.get("LEX_GENAUDIT_MODEL", "opencode/mimo-v2.6-flash-free")
    e2e_dest = (
        Path(tempfile.mkstemp(suffix=".json")[1])
        if check_only
        else RESULTS / f"cached_example_ocl_attested_run{run_id}.json"
    )
    code, log = _run(
        [
            sys.executable,
            str(RUN_E2E),
            "--real",
            "--model",
            model,
            "--bundle",
            str(
                REPO
                / "tests"
                / "frontier"
                / "frontier-generative-audit"
                / "fixtures"
                / "real_ocl_bundle.json"
            ),
            "--attestation",
            "--out",
            str(e2e_dest),
        ],
        env,
        timeout=1800,
    )
    e2e: Dict[str, Any] = {"exit_code": code, "out": str(e2e_dest), "model": model}
    if e2e_dest.exists():
        data = json.loads(e2e_dest.read_text())
        bundle_ids = {
            d["decision_id"] for d in data["audited_product_bundle"]["decisions"]
        }
        unknown = [c for c in data["cited_decision_ids"] if c not in bundle_ids]
        unknown_f = [
            f.get("decision_id")
            for f in data["adversarial_findings"]
            if f.get("decision_id") not in bundle_ids
        ]
        e2e.update(
            {
                "cited_decision_ids": data["cited_decision_ids"],
                "unknown_cited_ids": unknown,
                "redacted_citation_ids": data["redacted_citation_ids"],
                "unknown_finding_ids": unknown_f,
                "findings": len(data["adversarial_findings"]),
                "status_summary": data["status_summary"],
                "validation_mode": (data.get("citation_validation") or {}).get("mode"),
                "verified_ids": (data.get("citation_validation") or {}).get(
                    "verified_ids"
                ),
                "ok": code == 0 and not unknown and not unknown_f,
            }
        )
    else:
        e2e["ok"] = False
    if check_only:
        e2e_dest.unlink(missing_ok=True)
    out["ocl_attested_e2e"] = e2e
    return out


def build_matrix(run_id: str, checks: Dict[str, Any], live: bool) -> Dict[str, Any]:
    canon_ok = checks["suites"]["canonical_suite"]["ok"]
    legacy_ok = checks["suites"]["legacy_suite"]["ok"]
    fixture_ok = checks["fixture_e2e"]["ok"]
    live_bits = checks.get("live") or {}
    live_ok = all(v.get("ok") for v in live_bits.values()) if live_bits else None

    def verdict(ok: Any) -> str:
        return "PASS" if ok else ("NOT-RUN" if ok is None else "FAIL")

    return {
        "team_id": "frontier-generative-audit",
        "charter_version": 2,
        "run_id": run_id,
        "mode": "deterministic verify_cycle.py finisher (operational resume of snapshot 38193076995)",
        "resumed_from_snapshot_run": "38193076995",
        "contract_version": "generative-audit-contract/2.2",
        "canonical_tree": "frontier/frontier-generative-audit",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "checks": checks,
        "acceptance": {
            "1_provider_interface": {
                "status": verdict(canon_ok and fixture_ok and (live_ok in (True, None))),
                "evidence": [
                    "provider.py: OpenCode CLI (free model pool), OpenAI-compatible local server, deterministic fixture backends",
                    "canonical suite includes test_real_model_smoke (opt-in LEX_REAL_MODEL=1) and test_provider_fallback_across_models",
                    (
                        f"live free-model + OCL verification executed: {live}"
                    ),
                ],
            },
            "2_citation_constraint": {
                "status": verdict(fixture_ok and (live_ok in (True, None))),
                "evidence": [
                    "test_hallucinated_citation_rejection_and_redaction + test_fixture_rejects_invented_cited_ids",
                    f"fixture e2e unknown_cited_ids={checks['fixture_e2e'].get('unknown_cited_ids')} redacted={checks['fixture_e2e'].get('redacted_citation_ids')}",
                ],
            },
            "3_independent_adversarial_pass": {
                "status": verdict(canon_ok),
                "evidence": [
                    "test_adversarial_prompt_is_independent + test_adversarial_fixture_mode_challenge_only",
                    "separate challenge-only model call; unknown finding IDs rejected (test_adversarial_parse_rejects_unknown_ids)",
                ],
            },
            "4_structured_statuses": {
                "status": verdict(canon_ok and fixture_ok),
                "evidence": [
                    "test_structured_statuses_merging + test_unsupported_status_downgrade + test_cited_but_contrary_stays_visible_as_counter",
                    f"fixture e2e status_summary={checks['fixture_e2e'].get('status_summary')}",
                ],
            },
            "5_post_generation_validation": {
                "status": verdict(canon_ok and (live_ok in (True, None))),
                "evidence": [
                    "strict-local bundle validation always on; OpenCaseLaw attestation path sound (error/empty/mismatch/non-2xx -> unverified)",
                    (
                        "live attested e2e: "
                        + json.dumps(
                            {
                                k: live_bits.get(k, {}).get("ok")
                                for k in live_bits
                            }
                        )
                        if live_bits
                        else "live attestation not exercised in this invocation (set --live)"
                    ),
                ],
            },
            "6_end_to_end_cached_example": {
                "status": verdict(fixture_ok),
                "evidence": [
                    f"cached example written: {checks['fixture_e2e'].get('out')}",
                ],
            },
            "7_test_coverage": {
                "status": verdict(canon_ok and legacy_ok),
                "evidence": [
                    f"canonical suite {checks['suites']['canonical_suite'].get('passed')} passed / {checks['suites']['canonical_suite'].get('failed')} failed"
                    f"{' (live flags on)' if live else ' (offline)'}",
                    f"legacy accepted suite {checks['suites']['legacy_suite'].get('passed')} passed / {checks['suites']['legacy_suite'].get('failed')} failed",
                    "covers invented-citation rejection, unsupported-status downgrade, provider failure fallback, deterministic parsing",
                ],
            },
            "8_integration_contract": {
                "status": verdict(canon_ok),
                "evidence": [
                    "integration_contract.run_generative_audit one-call seam; test_run_generative_audit_end_to_end_contract + test_product_compat_uses_accepted_validator",
                    "README.md documents the product copy/adapt contract (2.2)",
                ],
            },
        },
        "overall": "PASS"
        if (canon_ok and legacy_ok and fixture_ok and (live_ok in (True, None)))
        else "FAIL",
        "claim_ceiling": "ACCEPTED engineering capability; live results are point-in-time CI observations of free providers and OpenCaseLaw public endpoints",
    }


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-id", required=True)
    ap.add_argument(
        "--live",
        action="store_true",
        help="also run live free-model + OpenCaseLaw probe/attested e2e (writes run-scoped artifacts)",
    )
    ap.add_argument(
        "--check-only",
        action="store_true",
        help="verify everything but write no evidence files",
    )
    args = ap.parse_args(argv)

    checks: Dict[str, Any] = {
        "suites": check_suites(live=args.live),
        "fixture_e2e": check_fixture_e2e(args.run_id, check_only=args.check_only),
    }
    if args.live:
        checks["live"] = check_live(args.run_id, check_only=args.check_only)

    matrix = build_matrix(args.run_id, checks, live=args.live)

    if not args.check_only:
        RESULTS.mkdir(parents=True, exist_ok=True)
        per_run = RESULTS / f"acceptance_matrix_run{args.run_id}.json"
        per_run.write_text(json.dumps(matrix, indent=2, ensure_ascii=False) + "\n")
        latest = RESULTS / "acceptance_matrix.json"
        latest.write_text(json.dumps(matrix, indent=2, ensure_ascii=False) + "\n")
        print(f"wrote {per_run}")
        print(f"wrote {latest}")

    print(json.dumps(matrix["acceptance"], indent=2, ensure_ascii=False))
    print(f"OVERALL: {matrix['overall']}")
    return 0 if matrix["overall"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
