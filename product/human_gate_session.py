"""One-command runner for the comparative human gate — the last product milestone.

Why this exists
---------------
Direction v51: the single remaining product milestone is the comparative human
gate, and it is answerable in one sitting *if* the owner only has to do the part
that requires a human. Before this runner the owner-facing path was:

    1. python product/query_app.py --port 8791        # terminal 1
    2. open http://127.0.0.1:8791/                    # run a query, use map <-> list
    3. press "Exporter la session"                    # a JSON download appears
    4. find that download, then find the bundle, then run the finalizer with the
       right flags                                             # terminal 2

Steps 3-4 are mechanical and were the source of the failure modes this lane was
repaired for: the finalizer was invoked without provenance (exit 7), and the
records it wrote were indistinguishable from test scratch. This runner closes
that loop: it serves the product, prints the four gate questions, watches for the
exported draft, finalizes it into ``results/product/human_gate_sessions/`` with
attested provenance, then runs the admissibility scanner and prints the verdict.

What it will never do
---------------------
* It never answers a gate question. The four answers are the jurist's words; a
  draft with missing answers is recorded as ``status: incomplete`` (exit 3) and
  still returned to the owner as evidence.
* It never writes ``human_gate_ready: true``. The director sets that, from the
  records, after reading them.
* ``--run-id`` / ``--operator`` are **attested**, not authenticated: the runner
  cannot tell an autonomous agent from an owner typing their own name. It records
  what it was told, and says so in every record it writes.

Usage
-----
    # the whole session, in one command
    python product/human_gate_session.py --port 8791 --run-id <run> --operator <name> --owner-session

    # offline rehearsal with the deterministic fixture corpus
    python product/human_gate_session.py --fixture --run-id <run> --operator <name> \
        --owner-session   # or drop --owner-session and pass --out <dir> to rehearse

    # finalize a draft that was already exported, without starting a server
    python product/human_gate_session.py finalize <draft.json> --bundle <bundle.json> \
        --run-id <run> --operator <name>

    # just re-check the evidence directories
    python product/human_gate_session.py check

Exit codes: the finalizer's (0 finalized, 3 incomplete, 4 invalid draft,
5 mismatch, 6 I/O, 7 provenance, 8 inadmissible) — see
:mod:`product.human_gate_finalize`; 9 when the watcher timed out without a draft.
"""
from __future__ import annotations

import argparse
import sys
import threading
import time
from pathlib import Path
from typing import Sequence

PRODUCT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PRODUCT_ROOT.parent
if str(PRODUCT_ROOT) not in sys.path:
    sys.path.insert(0, str(PRODUCT_ROOT))

import human_gate_evidence  # noqa: E402
import human_gate_finalize as hgf  # noqa: E402
from human_gate_finalize import GATE_QUESTIONS, FinalizeError, load_json  # noqa: E402

#: The harness names its download ``<session_id>.json`` or ``lex_session_draft.json``.
DRAFT_GLOBS = ("*session*.json", "lex_session_draft.json")


def owner_card(base_url: str) -> str:
    """The one sitting, printed once. This is the whole owner contract."""
    lines = [
        "",
        "=" * 78,
        " LexMachina comparative human gate — one sitting",
        "=" * 78,
        f"  1. Open {base_url}/ and run a real Swiss-law question.",
        "  2. Work the case in the MAP, then switch to LIST (the conventional",
        "     baseline) and work it again. Open the decisions and the counter",
        "     authorities in both views — the export records which you opened.",
        "  3. Answer these four questions (the harness marks them before export):",
    ]
    for qid, question in GATE_QUESTIONS.items():
        lines.append(f"       {qid}: {question}")
    lines += [
        "  4. Press \"Exporter la session\". This terminal watches for the",
        "     download, finalizes it against the exact bundle, and prints whether",
        "     the record is admissible as human-gate evidence.",
        "",
        " A \"no\" on any question is a valid, valuable result and is recorded as",
        " such. human_gate_ready is set by the director from these records, never",
        " by this tool. Press Ctrl-C to stop the server without a session.",
        "=" * 78,
        "",
    ]
    return "\n".join(lines)


def find_draft(watch_dir: Path, *, since: float | None = None) -> Path | None:
    """Newest harness export in ``watch_dir`` (mtime-filtered when given)."""
    candidates: list[Path] = []
    for pattern in DRAFT_GLOBS:
        for path in watch_dir.glob(pattern):
            if since is None or path.stat().st_mtime > since:
                candidates.append(path)
    return max(candidates, key=lambda p: p.stat().st_mtime) if candidates else None


def draft_query(draft: dict) -> str | None:
    ref = draft.get("bundle_ref") or {}
    return draft.get("query") or ref.get("query")


def resolve_live_bundle(draft: dict) -> tuple[dict | None, str]:
    """The exact bundle the session was run on, taken from the server we serve.

    The owner should never have to identify a bundle by hand. The runner serves
    the product in-process, so it reads the same in-memory run registry the UI
    reads and picks the most recent run whose query is the draft's query. Returns
    ``(bundle, source)``; ``bundle`` is ``None`` when nothing matches.
    """
    try:
        import query_app
    except Exception:  # pragma: no cover - server not importable
        return None, "server_unavailable"
    query = draft_query(draft)
    best: tuple[str, dict] | None = None
    with query_app.RUNS_LOCK:
        for run_id, record in query_app.RUNS.items():
            if query and record.get("query") != query:
                continue
            if not record.get("bundle"):
                continue
            if best is None or record.get("created_at", "") >= best[0]:
                best = (record.get("created_at", ""), record["bundle"])
    return (best[1], "server_run") if best else (None, "no_matching_run")


def finalize_draft(
    draft: dict,
    *,
    bundle: dict | None,
    run_id: str | None,
    operator: str | None,
    out_dir: Path,
    owner_session: bool = False,
) -> tuple[int, Path | None, dict | None]:
    """Finalize one exported draft. Returns (exit_code, written_path, record)."""
    try:
        record = hgf.finalize(
            draft, None, bundle, run_id=run_id, finalized_by=operator, owner_session=owner_session
        )
        path = hgf.write_record(record, out_dir)
    except hgf.IncompleteSession as incomplete:
        # A missing answer is still evidence: record it and tell the owner which.
        try:
            path = hgf.write_record(incomplete.record, out_dir)
        except FinalizeError as refused:
            print(f"::error::{refused}", file=sys.stderr)
            return refused.exit_code, None, None
        return incomplete.exit_code, path, incomplete.record
    except FinalizeError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return exc.exit_code, None, getattr(exc, "record", None)
    return 0, path, record


def serve(
    *,
    host: str = "127.0.0.1",
    port: int = 8791,
    fixture: bool = False,
    run_id: str | None = None,
    operator: str | None = None,
    watch_dir: Path = Path.cwd(),
    wait_s: float = 1800.0,
    verbose: bool = True,
    out_dir: Path | None = None,
    owner_session: bool = False,
) -> int:
    """Serve the product and finalize the exported draft when it lands."""
    from query_app import POOL, make_server  # local import: only the runner needs the server

    srv = make_server(host, port, fixture_mode=fixture, verbose=verbose)
    bound_port = srv.server_address[1]
    base_url = f"http://{host}:{bound_port}"
    if verbose:
        print(f"LexMachina query map ({'fixture/offline' if fixture else 'live OpenCaseLaw'}): {base_url}/")
        print(owner_card(base_url))
        print(f"watching {watch_dir} for the exported session draft (Ctrl-C to stop)")

    thread = threading.Thread(target=srv.serve_forever, name="lex-gate-server", daemon=True)
    thread.start()

    started = time.time()
    deadline = started + wait_s if wait_s > 0 else None
    draft_path: Path | None = None
    while draft_path is None:
        if deadline is not None and time.time() > deadline:
            print(f"\nno draft exported within {wait_s:.0f}s; stopping (the server stays available)")
            break
        time.sleep(0.5)
        candidate = find_draft(watch_dir, since=started)
        if candidate is not None and time.time() - candidate.stat().st_mtime >= 0.5:
            draft_path = candidate  # the browser finished writing it

    srv.shutdown()
    srv.server_close()
    POOL.shutdown(wait=False, cancel_futures=True)
    if draft_path is None:
        return 9

    print(f"\nexported draft: {draft_path}")
    try:
        draft = load_json(draft_path)
    except FinalizeError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return exc.exit_code
    bundle, source = resolve_live_bundle(draft if isinstance(draft, dict) else {})
    if bundle is None:
        print(f"::error::could not bind the session to the bundle it ran on ({source})", file=sys.stderr)
        print("           re-run with --bundle <the bundle you were looking at>", file=sys.stderr)
        return 5
    print(f"bound to the served bundle ({source}): {len(bundle.get('decisions') or [])} decisions")
    return finish(
        draft_path,
        run_id=run_id,
        operator=operator,
        bundle=bundle,
        out_dir=out_dir,
        owner_session=owner_session,
    )


def finish(
    draft_path: Path,
    *,
    run_id: str | None,
    operator: str | None,
    bundle: dict | None = None,
    bundle_path: Path | None = None,
    out_dir: Path | None = None,
    owner_session: bool = False,
) -> int:
    """Finalize a draft, then print the admissibility verdict. The whole tail."""
    target = out_dir or hgf.DEFAULT_OUT_DIR
    if bundle is None and bundle_path is not None:
        bundle = load_json(bundle_path)
    try:
        draft = load_json(draft_path)
    except FinalizeError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return exc.exit_code
    code, written, record = finalize_draft(
        draft, bundle=bundle, run_id=run_id, operator=operator, out_dir=target, owner_session=owner_session
    )
    if written is not None and code == 0:
        print(f"finalized: {written}")
    elif written is not None:
        print(f"recorded as incomplete evidence: {written}")
    if record is not None:
        print(
            f"  session={record['session_id']} status={record['status']} "
            f"bundle_hash_status={record['bundle_hash_status']} "
            f"opened={record['session_metrics']['n_decisions_opened']} "
            f"counters_opened={record['session_metrics']['n_counter_authorities_opened']} "
            f"used_baseline={record['session_metrics']['used_conventional_baseline']}"
        )
        if code == 3:
            print(f"  answers still required: {', '.join(record.get('missing_answers') or [])}")
    print("  human_gate_ready is NOT set by this tool; it records one session's evidence.")

    report = human_gate_evidence.scan()
    print(
        f"  evidence scan: {report['blocking_count']} blocking, {report['warning_count']} warning"
        f" -> {'ADMISSIBLE' if report['admissible'] else 'NOT ADMISSIBLE'}"
    )
    if not report["admissible"]:
        for finding in report["findings"]:
            if finding["severity"] == "blocking":
                print(f"    [blocking] {finding['code']}: {finding['record']}")
        return 8
    return code


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="One-command runner for the comparative human gate.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("Usage\n-----")[-1],
    )
    parser.add_argument("command", nargs="?", default="serve", choices=("serve", "finalize", "check"))
    parser.add_argument("draft", nargs="?", type=Path, default=None, help="exported draft (with 'finalize')")
    parser.add_argument("--bundle", type=Path, default=None, help="the query_result_bundle the session ran on")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8791)
    parser.add_argument("--fixture", action="store_true", help="deterministic offline corpus")
    parser.add_argument("--run-id", default=None, help="core-lane run this session belongs to (attested)")
    parser.add_argument("--operator", default=None, help="who is running the session (attested, free text)")
    parser.add_argument("--watch-dir", type=Path, default=None, help="where the browser download lands")
    parser.add_argument("--wait-s", type=float, default=1800.0, help="how long to wait for the export; 0 = forever")
    parser.add_argument("--out", type=Path, default=None, help="output directory (default: canonical)")
    parser.add_argument(
        "--owner-session",
        action="store_true",
        help="declare that a person is answering the four gate questions right now; "
        "required to write into the canonical evidence directory",
    )
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    if args.command == "check":
        return human_gate_evidence.main([])

    if args.command == "finalize":
        if args.draft is None:
            print("::error::finalize needs the exported draft path", file=sys.stderr)
            return 4
        return finish(
            args.draft,
            run_id=args.run_id,
            operator=args.operator,
            bundle_path=args.bundle,
            out_dir=args.out,
            owner_session=args.owner_session,
        )

    try:
        return serve(
            host=args.host,
            port=args.port,
            fixture=args.fixture,
            run_id=args.run_id,
            operator=args.operator,
            watch_dir=args.watch_dir or Path.cwd(),
            wait_s=args.wait_s,
            verbose=not args.quiet,
            out_dir=args.out,
            owner_session=args.owner_session,
        )
    except KeyboardInterrupt:  # pragma: no cover - interactive
        print("\nstopped without a session; nothing was recorded")
        return 0


if __name__ == "__main__":  # pragma: no cover - CLI
    sys.exit(main())