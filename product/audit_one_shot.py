#!/usr/bin/env python3
"""One command, offline, bounded: recompute every headline claim an independent product audit checks.

Why this module exists
----------------------
Three consecutive independent audits of this lane burned their entire 45-minute
work quantum (rc 78 ``LEX_WORK_QUANTUM_EXPIRED`` at step 5) *re-deriving claims
the producer had already made recomputable*:

* run 38988477028 audit — died because the obligation-(5) artifact had no
  committed producer (closed by ``product/rebuild_served_packet.py``);
* run 38993348615 audit — completed only by re-running, from scratch, a fresh
  venv, a five-file pytest suite, the DOM smoke, the rebuild ``--check``, the
  recall instrument and the state contract (its own ``evidence_summary`` is the
  specification of this tool);
* run 38995823263 audit — died rc 78 at the same step although the producer had
  succeeded and both prior required fixes were closed.

The checks themselves are sound and are NOT weakened here.  What is shipped is
the *packaging*: the exact check set the audits run, chained in one process,
each with a wall-clock bound, emitting one machine-readable record the auditor
can diff against the cycle report instead of rebuilding the environment by
hand.  Every subprocess is the product's own committed entry point, invoked
verbatim — this tool invents no gate, no threshold and no verdict.

Checks (all offline; no network, no provider, no LLM)
-----------------------------------------------------
1. ``state_contract``             — ``state_contract.py --check`` (workflow step 7/9 contract)
2. ``rebuild_served_packet_check``— ``rebuild_served_packet.py --check`` on the committed BJR leg
3. ``evidence_pack_recall_nc``    — ``evidence_pack_recall.py --negative-control --json`` (non-vacuity)
4. ``targeted_product_suite``     — pytest of the five product query suites the audits run
5. ``query_page_dom_smoke``       — ``node product/verify_query_page.js <accepted bundle>`` (SKIPPED without node)
6. ``forbidden_claims_scan``      — ``packet_admission.find_forbidden_claims`` over the cycle report + both artifacts
7. ``packet_admission_invariant`` — recomputes ``packet_admission()`` and enforces the accepted
                                    DO-NOT-SERVE contract: while the accepted verdict still carries a
                                    serve recommendation containing DO-NOT-SERVE, ``ready_for_owner_session``
                                    MUST be false (obligation (1); fail-closed invariant, not a gate change)

Usage
-----
    python product/audit_one_shot.py --run-id <run_id>            # write the record
    python product/audit_one_shot.py --run-id <id> --only state_contract,forbidden_claims_scan
    python product/audit_one_shot.py --list                        # list check names

Exit codes: 0 all required checks PASS (SKIPPED allowed); 1 a required check
failed; 2 bad arguments; 3 an internal error.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

PRODUCT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PRODUCT_ROOT.parent
for _p in (str(PRODUCT_ROOT), str(REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

SCHEMA = "product/audit-one-shot/1"

#: The committed live BJR bundle + its leg artifact: the obligation-(5) headline
#: evidence every recent audit recomputes.  Frozen inputs, not tuned.
BJR_BUNDLE = REPO_ROOT / "results/product/CYCLE_38984833779/bundle_business-judgment-rule_live.json"
BJR_LEG = REPO_ROOT / "results/product/CYCLE_38984833779/leg_business-judgment-rule_live.json"
BJR_SLUG = "business-judgment-rule"
BJR_RUN_ID = "38984833779"

#: The accepted clickable-slice bundle the audits DOM-smoke (37 assertions).
DOM_SMOKE_BUNDLE = REPO_ROOT / "results/product/clickable_slice/bundle_live_enriched_20261014T214600Z.json"

#: The suites the audits run, in the audits' own order, plus this tool's own
#: suite (fast, offline, and it must stay green for the packaging to be sound).
TARGETED_SUITES = (
    "product/tests/test_rebuild_served_packet.py",
    "product/tests/test_evidence_pack_recall.py",
    "product/tests/test_query_map_mvp.py",
    "product/tests/test_packet_admission.py",
    "product/tests/test_state_contract.py",
    "product/tests/test_audit_one_shot.py",
)

#: Default per-check wall-clock bounds (seconds).  The pytest bound matches the
#: ~25 s the suite takes locally, with generous headroom for a cold venv.
DEFAULT_TIMEOUTS = {
    "state_contract": 120.0,
    "rebuild_served_packet_check": 300.0,
    "evidence_pack_recall_nc": 300.0,
    "targeted_product_suite": 900.0,
    "query_page_dom_smoke": 300.0,
    "forbidden_claims_scan": 60.0,
    "packet_admission_invariant": 60.0,
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    """Repo-relative display form for a path; absolute fallback outside the repo."""
    try:
        return str(Path(path).resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _tail(text: str, limit: int = 2000) -> str:
    text = text or ""
    return text if len(text) <= limit else "..." + text[-limit:]


def _run(argv: list[str], timeout: float) -> tuple[int, str, str, float, str | None]:
    """Run a subprocess with a bound.  Returns (rc, stdout, stderr, seconds, timeout_note)."""
    t0 = time.monotonic()
    try:
        proc = subprocess.run(
            argv, cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=timeout
        )
        return proc.returncode, proc.stdout, proc.stderr, time.monotonic() - t0, None
    except subprocess.TimeoutExpired as exc:
        elapsed = time.monotonic() - t0
        out = (exc.stdout or b"").decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        err = (exc.stderr or b"").decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return 124, out, err or f"timeout after {timeout}s", elapsed, f"TIMEOUT after {timeout}s"


# --------------------------------------------------------------------------- #
# individual checks — each returns a record dict
# --------------------------------------------------------------------------- #

def check_state_contract(timeout: float) -> dict[str, Any]:
    rc, out, err, secs, note = _run(
        [sys.executable, "product/state_contract.py", "--check"], timeout
    )
    return {
        "verdict": "PASS" if rc == 0 else "FAIL",
        "command": "python product/state_contract.py --check",
        "rc": rc,
        "seconds": round(secs, 3),
        "timeout": note,
        "stdout_tail": _tail(out),
        "stderr_tail": _tail(err),
        "key_findings": {"workflow_state_contract": "PASS" if rc == 0 else "FAIL"},
    }


def check_rebuild_served_packet(timeout: float) -> dict[str, Any]:
    argv = [
        sys.executable, "product/rebuild_served_packet.py",
        "--bundle", _rel(BJR_BUNDLE),
        "--slug", BJR_SLUG, "--run-id", BJR_RUN_ID,
        "--reference", _rel(BJR_LEG),
        "--check",
    ]
    rc, out, err, secs, note = _run(argv, timeout)
    reproduced = rc == 0 and "OK: rebuild reproduces" in out
    key: dict[str, Any] = {"reproduces_19_fields": bool(reproduced)}
    try:
        leg = json.loads(BJR_LEG.read_text(encoding="utf-8"))
        key["recall_gate_recall_controlling_authority"] = leg.get(
            "recall_gate_recall_controlling_authority")
        key["mega_cluster_disclosure_size_based"] = leg.get("mega_cluster_disclosure")
        key["largest_cluster_size_share"] = leg.get("largest_cluster_size_share")
        admission = leg.get("packet_admission") or {}
        key["packet_admission_blocked_by"] = admission.get("blocked_by")
        key["ready_for_owner_session"] = admission.get("ready_for_owner_session")
    except (OSError, ValueError) as exc:
        key["reference_read_error"] = str(exc)
    return {
        "verdict": "PASS" if reproduced else "FAIL",
        "command": " ".join(argv),
        "rc": rc,
        "seconds": round(secs, 3),
        "timeout": note,
        "stdout_tail": _tail(out),
        "stderr_tail": _tail(err),
        "key_findings": key,
    }


def check_evidence_pack_recall_nc(timeout: float) -> dict[str, Any]:
    rc, out, err, secs, note = _run(
        [sys.executable, "product/evidence_pack_recall.py", "--negative-control", "--json"],
        timeout,
    )
    key: dict[str, Any] = {}
    observable = False
    try:
        report = json.loads(out)
        bjr = report.get("controlling_authority_recall") or {}
        key["bjr_direct_in_evidence_pack"] = (
            f"{bjr.get('business_judgment_rule_direct_in_evidence_pack')}"
            f"/{bjr.get('business_judgment_rule_direct_total')}"
        )
        key["per_leg_direct_in_pack"] = {
            leg.get("slug"): f"{leg.get('direct_in_evidence_pack')}/{leg.get('direct_total')}"
            for leg in report.get("legs", [])
        }
        key["retrieval_misses"] = {
            leg.get("slug"): leg.get("retrieval_miss_ids")
            for leg in report.get("legs", []) if leg.get("retrieval_miss_ids")
        }
        nc = report.get("negative_control") or {}
        key["negative_control"] = {
            "baseline_in_evidence_pack": nc.get("baseline_in_evidence_pack"),
            "ablated_in_evidence_pack": nc.get("ablated_in_evidence_pack"),
            "mechanism_observable": nc.get("mechanism_observable"),
        }
        observable = bool(nc.get("mechanism_observable"))
    except ValueError as exc:
        key["json_parse_error"] = str(exc)
    # The instrument's own exit code encodes non-vacuity; recall values are
    # REPORTED, never gated here (frozen-bar measurement is Core Evaluation's).
    verdict = "PASS" if (rc == 0 and observable) else "FAIL"
    return {
        "verdict": verdict,
        "command": "python product/evidence_pack_recall.py --negative-control --json",
        "rc": rc,
        "seconds": round(secs, 3),
        "timeout": note,
        "stdout_tail": _tail(out),
        "stderr_tail": _tail(err),
        "key_findings": key,
        "claim_note": ("recall values are reported, not gated; the only enforced property "
                       "is the documented non-vacuity negative control"),
    }


def check_targeted_product_suite(timeout: float) -> dict[str, Any]:
    argv = [sys.executable, "-m", "pytest", *TARGETED_SUITES, "-q"]
    rc, out, err, secs, note = _run(argv, timeout)
    passed = failed = None
    m = re.search(r"(\d+) passed", out)
    if m:
        passed = int(m.group(1))
    m = re.search(r"(\d+) failed", out)
    if m:
        failed = int(m.group(1))
    ok = rc == 0 and (failed in (None, 0))
    return {
        "verdict": "PASS" if ok else "FAIL",
        "command": " ".join(argv),
        "rc": rc,
        "seconds": round(secs, 3),
        "timeout": note,
        "stdout_tail": _tail(out),
        "stderr_tail": _tail(err),
        "key_findings": {"passed": passed, "failed": failed if failed is not None else 0,
                         "suites": list(TARGETED_SUITES)},
    }


def check_query_page_dom_smoke(timeout: float) -> dict[str, Any]:
    if shutil.which("node") is None:
        return {
            "verdict": "SKIPPED",
            "command": "node product/verify_query_page.js <accepted bundle>",
            "rc": None,
            "seconds": 0.0,
            "timeout": None,
            "key_findings": {"reason": "node not available in this environment"},
        }
    argv = ["node", "product/verify_query_page.js", _rel(DOM_SMOKE_BUNDLE)]
    rc, out, err, secs, note = _run(argv, timeout)
    m = re.search(r"PASS (\d+) assertions", out)
    assertions = int(m.group(1)) if m else None
    ok = rc == 0 and "PASS " in out
    return {
        "verdict": "PASS" if ok else "FAIL",
        "command": " ".join(argv),
        "rc": rc,
        "seconds": round(secs, 3),
        "timeout": note,
        "stdout_tail": _tail(out),
        "stderr_tail": _tail(err),
        "key_findings": {"assertions_passed": assertions},
    }


def check_forbidden_claims_scan(timeout: float, report: Path | None = None) -> dict[str, Any]:
    from packet_admission import find_forbidden_claims
    t0 = time.monotonic()
    targets: list[Path] = [BJR_LEG]
    http_slice = REPO_ROOT / "results/product/CYCLE_38984833779/http_vertical_slice_b5304ed11825.json"
    if http_slice.exists():
        targets.append(http_slice)
    if report is not None:
        resolved = report if report.is_absolute() else (REPO_ROOT / report)
        targets.insert(0, resolved)
    hits: dict[str, list[dict]] = {}
    scanned: list[str] = []
    for path in targets:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            hits[str(path)] = [{"sentence": f"unreadable: {exc}", "pattern": None}]
            continue
        scanned.append(_rel(path))
        found = find_forbidden_claims(text)
        if found:
            hits[_rel(path)] = found
    secs = time.monotonic() - t0
    return {
        "verdict": "PASS" if not hits else "FAIL",
        "command": "packet_admission.find_forbidden_claims (in-process)",
        "rc": 0 if not hits else 1,
        "seconds": round(secs, 3),
        "timeout": None,
        "key_findings": {"scanned": scanned, "forbidden_claim_hits": hits},
    }


def check_packet_admission_invariant(timeout: float) -> dict[str, Any]:
    """Obligation (1), executable: while the accepted verdict carries the
    DO-NOT-SERVE recommendation, packet admission MUST block the owner session.
    """
    t0 = time.monotonic()
    from packet_admission import packet_admission, load_verdict, DO_NOT_SERVE
    verdict = load_verdict()
    admission = packet_admission()
    do_not_serve = bool(
        verdict and DO_NOT_SERVE in str(verdict.get("serve_recommendation") or "").upper()
    )
    ready = admission.get("ready_for_owner_session")
    if verdict is None:
        verdict_ok = admission.get("blocked_by") == ["no_accepted_verdict"] and ready is False
    elif do_not_serve:
        verdict_ok = ready is False and "accepted_do_not_serve_order" in (
            admission.get("blocked_by") or [])
    else:
        verdict_ok = True  # no standing order: admission is fully derived, nothing to enforce
    secs = time.monotonic() - t0
    return {
        "verdict": "PASS" if verdict_ok else "FAIL",
        "command": "packet_admission.packet_admission (in-process)",
        "rc": 0 if verdict_ok else 1,
        "seconds": round(secs, 3),
        "timeout": None,
        "key_findings": {
            "do_not_serve_order_active": do_not_serve,
            "ready_for_owner_session": ready,
            "human_gate_ready": admission.get("human_gate_ready"),
            "blocked_by": admission.get("blocked_by"),
            "verdict_team": admission.get("verdict_team"),
            "verdict_run": admission.get("verdict_run"),
        },
    }


# --------------------------------------------------------------------------- #
# registry + driver
# --------------------------------------------------------------------------- #

Runner = Callable[..., dict[str, Any]]

CHECKS: dict[str, Runner] = {
    "state_contract": check_state_contract,
    "rebuild_served_packet_check": check_rebuild_served_packet,
    "evidence_pack_recall_nc": check_evidence_pack_recall_nc,
    "targeted_product_suite": check_targeted_product_suite,
    "query_page_dom_smoke": check_query_page_dom_smoke,
    "forbidden_claims_scan": check_forbidden_claims_scan,
    "packet_admission_invariant": check_packet_admission_invariant,
}


def run_checks(
    names: list[str] | None = None,
    *,
    report: Path | None = None,
    timeouts: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    selected = names or list(CHECKS)
    unknown = [n for n in selected if n not in CHECKS]
    if unknown:
        raise ValueError(f"unknown check(s): {unknown}; known: {list(CHECKS)}")
    records: list[dict[str, Any]] = []
    for name in selected:
        timeout = (timeouts or {}).get(name, DEFAULT_TIMEOUTS.get(name, 300.0))
        if name == "forbidden_claims_scan":
            rec = CHECKS[name](timeout, report=report)
        else:
            rec = CHECKS[name](timeout)
        rec = {"name": name, **rec}
        records.append(rec)
    return records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run-id", default=None,
                        help="run id for the emitted record (default: GITHUB_RUN_ID or 'local')")
    parser.add_argument("--only", default=None,
                        help="comma-separated subset of check names")
    parser.add_argument("--list", action="store_true", help="list check names and exit")
    parser.add_argument("--report", type=Path, default=None,
                        help="cycle report to include in the forbidden-claims scan")
    parser.add_argument("--timeout", action="append", default=[],
                        metavar="CHECK=SECONDS", help="override a per-check timeout")
    parser.add_argument("--out", type=Path, default=None,
                        help="record path (default results/product/audit_one_shot/CYCLE_<run>_audit_one_shot.json)")
    args = parser.parse_args(argv)

    if args.list:
        for name in CHECKS:
            print(name)
        return 0

    run_id = args.run_id or __import__("os").environ.get("GITHUB_RUN_ID") or "local"
    names = [n.strip() for n in args.only.split(",")] if args.only else None
    timeouts: dict[str, float] = {}
    for item in args.timeout:
        if "=" not in item:
            print(f"bad --timeout {item!r}; expected CHECK=SECONDS", file=sys.stderr)
            return 2
        k, v = item.split("=", 1)
        try:
            timeouts[k.strip()] = float(v)
        except ValueError:
            print(f"bad --timeout seconds in {item!r}", file=sys.stderr)
            return 2

    started = _utc_now()
    t0 = time.monotonic()
    try:
        records = run_checks(names, report=args.report, timeouts=timeouts)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    wall = time.monotonic() - t0

    failed = [r["name"] for r in records if r["verdict"] == "FAIL"]
    skipped = [r["name"] for r in records if r["verdict"] == "SKIPPED"]
    passed = [r["name"] for r in records if r["verdict"] == "PASS"]
    overall = "PASS" if not failed else "FAIL"

    record = {
        "schema": SCHEMA,
        "run_id": run_id,
        "started_at": started,
        "finished_at": _utc_now(),
        "wall_seconds": round(wall, 3),
        "environment": {
            "python": sys.version.split()[0],
            "repo_root": str(REPO_ROOT),
        },
        "overall": overall,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "checks": records,
        "claim_ceiling": [
            "This record recomputes the lane's headline claims with the product's own committed "
            "entry points, offline; it asserts no gate the product does not already own.",
            "Recall values from evidence_pack_recall are REPORTED, not gated; frozen-bar "
            "measurement is Core Evaluation's.",
            "human_gate_ready and machine_gate_ready are NOT decided here; packet admission is "
            "recomputed and the accepted DO-NOT-SERVE invariant is enforced as a fail-closed check.",
        ],
    }
    out_path = args.out or (
        REPO_ROOT / "results/product/audit_one_shot" / f"CYCLE_{run_id}_audit_one_shot.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"audit_one_shot overall={overall} wall={record['wall_seconds']}s "
          f"passed={len(passed)} failed={len(failed)} skipped={len(skipped)}")
    for r in records:
        print(f"  [{r['verdict']:7s}] {r['name']:28s} {r['seconds']}s")
        kf = r.get("key_findings") or {}
        if kf:
            print(f"           {json.dumps(kf, ensure_ascii=False)[:400]}")
    print(f"record: {_rel(out_path)}")
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":  # pragma: no cover - CLI
    sys.exit(main())
