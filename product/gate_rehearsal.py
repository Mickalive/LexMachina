"""One-command rehearsal of the whole human-gate chain, offline or live.

    python product/gate_rehearsal.py --fixture          # offline, deterministic
    python product/gate_rehearsal.py --live --query "…" # real OpenCaseLaw

Why this exists
---------------
Direction v51 names *"finalize an exported session draft into results/product/
via the accepted CLI"* as an owner-independent delta, and two consecutive audits
named the same next step: exercise the runner against a **live** (non-fixture)
session end to end. Until now the export half of that chain was produced by an
ad-hoc node harness that was never committed, so nobody — including a test —
could reproduce:

    query -> progressive bundle -> REAL page in a real DOM -> accepted switch
    -> "Exporter la session" -> accepted finalizer -> evidence scanner

This script is that chain as a single command. It starts the accepted
one-command runner, drives the product's own HTTP API (first page -> expansion
-> answer/counter pass), runs ``product/export_session_draft.js`` against the
bundle the server is actually serving, and lets the runner watch, bind, finalize
and scan — the same code paths the owner runs, not a shortcut around them.

Honesty rules (same as the runner's):
* a machine rehearsal passes ``--simulated`` (the default here) and may only
  land in the simulated evidence directory, under the SIMULATED claim ceiling;
* ``--owner-session`` is refused: no script can declare a human session;
* answers come from an explicit ``--answers`` file through the page's answer
  card; without it the card stays empty and the record is honestly `incomplete`.

Exit codes: 0 chain completed and the evidence scan is admissible (a record with
status `incomplete` still counts — it is evidence too), 1 chain or scan failed,
4 node/driver unavailable, 5 bad input.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

PRODUCT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PRODUCT_ROOT.parent
if str(PRODUCT_ROOT) not in sys.path:
    sys.path.insert(0, str(PRODUCT_ROOT))

import human_gate_evidence  # noqa: E402
import human_gate_session as runner  # noqa: E402
from human_gate_finalize import SIMULATED_OUT_DIR  # noqa: E402

NODE = shutil.which("node")
DRIVER = PRODUCT_ROOT / "export_session_draft.js"

DEFAULT_QUERY = "Kündigung Mietvertrag Mietrecht"


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def http_json(url: str, *, timeout: float) -> tuple[dict, float]:
    """GET a JSON endpoint. Returns (payload, wall seconds). Non-2xx raises."""
    started = time.time()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            code = resp.status
    except urllib.error.HTTPError as exc:  # the enrich blocking form answers 500 on job error
        body = exc.read().decode("utf-8", "replace")
        raise RuntimeError(f"HTTP {exc.code} for {url}: {body[:400]}") from exc
    if code >= 400:  # pragma: no cover - urlopen raises first
        raise RuntimeError(f"HTTP {code} for {url}")
    return payload, round(time.time() - started, 4)


def _wait_health(base: str, *, limit_s: float = 30.0) -> None:
    deadline = time.time() + limit_s
    last: Exception | None = None
    while time.time() < deadline:
        try:
            http_json(f"{base}/api/health", timeout=5)
            return
        except Exception as exc:  # server still binding
            last = exc
            time.sleep(0.2)
    raise RuntimeError(f"server did not become healthy within {limit_s}s: {last}")


def _counter_ids(bundle: dict) -> list[str]:
    """Real counter authorities only - the accepted single source of truth.

    RF1: this used the broad ``counter_status != "none"`` test, so every row the
    sourced answer cited (``cited``) and every recall-only row
    (``supporting-candidate`` / ``context`` / ``unclassified``) counted as a
    counter authority. Delegated to
    ``gate_admissibility.counter_authority_ids`` so the rehearsal can never
    drift from the gate packet's own number.
    """
    from query.gate_admissibility import counter_authority_ids

    return counter_authority_ids(bundle.get("decisions") or [])


def _wake_runner(watch: Path, draft_path: Path, thread: threading.Thread, *, limit_s: float = 30.0) -> None:
    """Let the runner's watcher exit after a failed chain instead of leaking.

    The watcher blocks until a draft appears. When the chain fails BEFORE a real
    draft exists, an empty object is written under the same glob: the runner
    wakes, ``validate_draft`` rejects it (exit 4) or bundle binding fails
    (exit 5), and the thread returns without writing any record. The real draft,
    if one exists, is never touched.
    """
    if draft_path.exists() or thread.is_alive() is False:
        thread.join(timeout=limit_s)
        return
    try:
        watch.mkdir(parents=True, exist_ok=True)
        (watch / "lex_session_draft.json").write_text("{}\n", encoding="utf-8")
    finally:
        thread.join(timeout=limit_s)


def _scan_evidence(out_dir: Path) -> dict[str, Any]:
    """Admissibility of BOTH the repository evidence tree and the run's own target.

    ``human_gate_evidence.scan()`` with no arguments reads the two repository
    directories (canonical + simulated). A rehearsal that writes somewhere else
    must still have its own record judged, otherwise the summary would claim a
    verdict about directories the run did not touch.
    """
    repo_dirs = {
        Path(human_gate_evidence.CANONICAL_DIR).resolve(),
        Path(human_gate_evidence.SIMULATED_DIR).resolve(),
    }
    reports = [human_gate_evidence.scan()]
    if Path(out_dir).resolve() not in repo_dirs:
        reports.append(human_gate_evidence.scan([Path(out_dir)]))
    findings = [f for report in reports for f in report["findings"]]
    blocking = [f for f in findings if f["severity"] == "blocking"]
    return {
        "scanned": [s for report in reports for s in report["scanned"]],
        "findings": findings,
        "blocking_count": len(blocking),
        "warning_count": len(findings) - len(blocking),
        "admissible": not blocking,
    }


def run_rehearsal(args: argparse.Namespace) -> dict[str, Any]:
    """Execute the chain; return the summary (never raises for chain failures)."""
    summary: dict[str, Any] = {
        "record_type": "lex_gate_rehearsal",
        "generated_at": _now(),
        "mode": "live" if args.live else "fixture",
        "query": args.query,
        "run_id": args.run_id,
        "operator": args.operator,
        "claim_ceiling": (
            "SIMULATED REHEARSAL: machine-executed chain evidence only. Not a jurist "
            "session, never human-gate evidence; human_gate_ready stays false."
        ),
        "stages": {},
        "ok": False,
    }
    if NODE is None or not DRIVER.is_file():
        summary["error"] = "node or product/export_session_draft.js unavailable"
        return summary

    work = Path(args.work_dir) if args.work_dir else Path(tempfile.mkdtemp(prefix="lex_gate_rehearsal_"))
    work.mkdir(parents=True, exist_ok=True)
    watch = work / "downloads"
    watch.mkdir(exist_ok=True)
    draft_path = watch / "lex_session_draft.json"
    out_dir = Path(args.out) if args.out else SIMULATED_OUT_DIR
    port = args.port or free_port()
    base = f"http://127.0.0.1:{port}"
    summary.update({"work_dir": str(work), "out_dir": str(out_dir), "port": port, "base_url": base})

    answers_path = Path(args.answers) if args.answers else None
    if answers_path and not answers_path.is_file():
        summary["error"] = f"answers file not found: {answers_path}"
        return summary

    # --- 1. the accepted runner, in a thread (it owns server + watcher) ------
    outcome: dict[str, Any] = {"code": None}
    runner_kwargs: dict[str, Any] = dict(
        host="127.0.0.1",
        port=port,
        fixture=not args.live,
        run_id=args.run_id,
        operator=args.operator,
        watch_dir=watch,
        wait_s=args.wait_s,
        verbose=not args.quiet,
        out_dir=out_dir,
        owner_session=False,   # a rehearsal may never declare a human session
        simulated=True,
    )

    def _serve() -> None:
        outcome["code"] = runner.serve(**runner_kwargs)

    server_thread = threading.Thread(target=_serve, name="lex-rehearsal-runner", daemon=True)
    server_thread.start()

    try:
        _wait_health(base)

        # --- 2. drive the product's own API (progressive pipeline) ----------
        t0 = time.time()
        first, http_start = http_json(
            f"{base}/api/query/start?" + urllib.parse.urlencode({"q": args.query, "n": args.n}),
            timeout=args.stage_timeout_s,
        )
        server_run_id = first["run_id"]
        summary["stages"]["start"] = {
            "http_s": http_start,
            "wall_s": round(time.time() - t0, 4),
            "decisions": len(first["bundle"]["decisions"]),
            "phase": first["bundle"]["provenance"]["phase"],
        }
        t1 = time.time()
        exp, http_expand = http_json(
            f"{base}/api/query/expand?"
            + urllib.parse.urlencode({"run_id": server_run_id, "wait_s": args.wait_s}),
            timeout=args.wait_s + 60,
        )
        summary["stages"]["expand"] = {
            "http_s": http_expand,
            "wall_s": round(time.time() - t1, 4),
            "job": (exp.get("job") or {}).get("status"),
            "detail": (exp.get("job") or {}).get("detail") or {},
        }
        t2 = time.time()
        enr, http_enrich = http_json(
            f"{base}/api/query/enrich?"
            + urllib.parse.urlencode({"run_id": server_run_id, "wait_s": args.wait_s}),
            timeout=args.wait_s + 60,
        )
        summary["stages"]["enrich"] = {
            "http_s": http_enrich,
            "wall_s": round(time.time() - t2, 4),
            "job": (enr.get("job") or {}).get("status") or enr.get("status"),
        }
        bundle_resp, _ = http_json(
            f"{base}/api/query/bundle?" + urllib.parse.urlencode({"run_id": server_run_id}),
            timeout=60,
        )
        bundle = bundle_resp["bundle"]
    except Exception as exc:
        summary["error"] = f"query pipeline failed: {type(exc).__name__}: {exc}"
        _wake_runner(watch, draft_path, server_thread)
        return summary

    bundle_path = work / "bundle.json"
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
    timing = (bundle.get("provenance") or {}).get("timing") or {}
    answer = bundle.get("answer") or {}
    summary["bundle"] = {
        "n_decisions": len(bundle.get("decisions") or []),
        "n_clusters": len(bundle.get("clusters") or []),
        "n_counter": len(_counter_ids(bundle)),
        "n_relations": len(bundle.get("relations") or []),
        "answer_status": answer.get("status"),
        "answer_method": answer.get("method"),
        "answer_model": answer.get("model"),
        "cited": len(answer.get("cited_decision_ids") or []),
        "provenance_timing": timing,
        "request_summary": ((bundle.get("provenance") or {}).get("retrieval") or {})
        .get("remote", {})
        .get("request_summary"),
    }

    # --- 3. the export half: REAL page -> accepted switch -> draft ----------
    driver_cmd = [
        NODE, str(DRIVER),
        "--bundle", str(bundle_path),
        "--out", str(draft_path),
    ]
    if answers_path:
        driver_cmd += ["--answers", str(answers_path)]
    if args.session_id:
        driver_cmd += ["--session-id", args.session_id]
    started = time.time()
    proc = subprocess.run(driver_cmd, capture_output=True, text=True, cwd=str(REPO_ROOT))
    summary["driver"] = {
        "cmd": driver_cmd,
        "exit_code": proc.returncode,
        "elapsed_s": round(time.time() - started, 4),
        "stdout": proc.stdout[-4000:],
        "stderr": proc.stderr[-2000:],
    }
    if proc.returncode != 0:
        summary["error"] = "session export driver failed (the page/switch chain is broken)"
        _wake_runner(watch, draft_path, server_thread)
        return summary

    # --- 4. the runner watches, binds to ITS run registry, finalizes --------
    server_thread.join(timeout=args.wait_s + 60)
    summary["runner"] = {
        "exit_code": outcome["code"],
        "thread_alive": server_thread.is_alive(),
        "draft_found": draft_path.is_file(),
    }
    if outcome["code"] is None:
        summary["error"] = "runner never returned (draft was not picked up)"
        return summary

    records = sorted(out_dir.glob("session_*.json"), key=lambda p: p.stat().st_mtime)
    record = json.loads(records[-1].read_text(encoding="utf-8")) if records else None
    if record is not None:
        summary["runner"].update(
            {
                "record_path": str(records[-1]),
                "session_id": record.get("session_id"),
                "status": record.get("status"),
                "simulated": record.get("simulated"),
                "bundle_hash_status": record.get("bundle_hash_status"),
                "owner_session_confirmed": record.get("owner_session_confirmed"),
                "missing_answers": record.get("missing_answers"),
                "claim_ceiling": record.get("claim_ceiling"),
                "session_metrics": record.get("session_metrics"),
                "answers": record.get("answers"),
            }
        )

    # --- 5. admissibility, independently of the runner's own printout -------
    scan = _scan_evidence(out_dir)
    summary["evidence_scan"] = scan
    summary["ok"] = bool(
        outcome["code"] in (0, 3)
        and scan["admissible"]
        and record is not None
        and record.get("simulated") is True
    )
    if not summary["ok"] and "error" not in summary:
        summary["error"] = (
            f"chain incomplete: runner_exit={outcome['code']} admissible={scan['admissible']} "
            f"record={'found' if record else 'missing'}"
        )
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--live", action="store_true", help="real OpenCaseLaw + real free model")
    mode.add_argument("--fixture", action="store_true", help="deterministic offline run (default)")
    parser.add_argument("--query", default=DEFAULT_QUERY)
    parser.add_argument("--n", type=int, default=150, help="target decisions for the map")
    parser.add_argument("--run-id", default="rehearsal", help="attested core-lane run id")
    parser.add_argument("--operator", default="autonomous-rehearsal", help="attested operator")
    parser.add_argument("--port", type=int, default=0, help="0 = pick a free port")
    parser.add_argument("--work-dir", default=None, help="where bundle/draft land (default: temp)")
    parser.add_argument("--out", default=None, help="record directory (default: simulated evidence dir)")
    parser.add_argument("--answers", default=None, help="answers JSON fed through the page's answer card")
    parser.add_argument("--session-id", default=None, help="session id for the exported draft")
    parser.add_argument("--wait-s", type=float, default=900.0, help="per-stage wait budget")
    parser.add_argument("--stage-timeout-s", type=float, default=600.0)
    parser.add_argument("--summary", default=None, help="write the JSON summary to this path")
    parser.add_argument("--quiet", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.live:
        args.fixture = True

    summary = run_rehearsal(args)
    text = json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True)
    if args.summary:
        path = Path(args.summary)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
    if not args.quiet:
        print(text)
        if "error" in summary:
            print(f"REHEARSAL FAILED: {summary['error']}", file=sys.stderr)
        else:
            scan = summary["evidence_scan"]
            print(
                f"REHEARSAL {'OK' if summary['ok'] else 'NOT OK'}: "
                f"runner_exit={summary['runner']['exit_code']} "
                f"record={summary['runner'].get('status')} "
                f"scan={scan['blocking_count']} blocking / {scan['warning_count']} warning "
                f"-> {'ADMISSIBLE' if scan['admissible'] else 'NOT ADMISSIBLE'}"
            )
    return 0 if summary.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
