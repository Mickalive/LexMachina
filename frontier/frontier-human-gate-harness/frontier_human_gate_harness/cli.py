"""One-command offline owner harness.

    cd frontier/frontier-human-gate-harness
    python -m frontier_human_gate_harness.cli --fixture <bundle> --out <dir>

produces (with no network access):

* ``baseline_view.html``   — the conventional ranked-list baseline (acceptance 1)
* ``owner_card_fr.html`` / ``owner_card_de.html`` / ``owner_card.json`` (acceptance 3)
* ``session_<id>.json``    — an explicit *empty* capture (acceptance 4/5)
* ``harness_demo.html``    — the clickable list<->map-switch + card + capture slice
* ``summary.json``         — what was written, with hashes

and the capture side:

    python -m frontier_human_gate_harness.cli --finalize <draft.json> [...] \
        --out results/frontier/frontier-human-gate-harness

writes ``session_<id>.json`` for a real owner sitting, rejecting a missing
answer instead of inventing one (acceptance 4/6).

Exit codes: 0 ok · 2 capture/validation error · 3 missing bundle field
(charter TERMINATE rule) · 4 usage error.
"""
from __future__ import annotations

import argparse
import json
import socket
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from . import __version__
from .baseline_view import build_model, render_document, render_summary
from .bundle_io import (BundleError, MissingBundleFieldError, bundle_sha256,
                        load_bundle, product_contract_errors,
                        query_sha256, require_conventional_fields,
                        validate_bundle_mirror)
from .capture import (CaptureError, MissingAnswerError, empty_capture, finalize,
                      read_draft, write_session)
from .owner_card import card_json_bytes, render_card_document

EXIT_OK = 0
EXIT_CAPTURE = 2
EXIT_BUNDLE_FIELD = 3
EXIT_USAGE = 4


class NetworkDisabled(RuntimeError):
    """Raised if anything in the harness tries to open a network connection."""


@contextmanager
def offline_only() -> Iterator[None]:
    """Hard offline guarantee: block every outbound connection for this run."""
    def blocked(*_args, **_kwargs):
        raise NetworkDisabled(
            "network access blocked: frontier-human-gate-harness runs offline"
        )

    targets = [
        (socket.socket, "connect"),
        (socket.socket, "connect_ex"),
        (socket.socket, "sendto"),
        (socket, "create_connection"),
        (socket, "getaddrinfo"),
    ]
    originals = [(target, attr, getattr(target, attr)) for target, attr in targets]
    for target, attr in targets:
        setattr(target, attr, blocked)
    try:
        yield
    finally:
        for target, attr, value in originals:
            setattr(target, attr, value)


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def run_fixture_mode(args: argparse.Namespace) -> int:
    bundle = load_bundle(args.fixture)
    try:
        require_conventional_fields(bundle)
    except MissingBundleFieldError as exc:
        print(f"3: {exc}", file=sys.stderr)
        return EXIT_BUNDLE_FIELD

    mirror_errors = validate_bundle_mirror(bundle)
    product_errors = product_contract_errors(bundle)
    sha = bundle_sha256(bundle)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    written: list[str] = []

    baseline_path = out / "baseline_view.html"
    baseline_path.write_text(render_document(bundle), encoding="utf-8")
    written.append(str(baseline_path))

    for lang in ("fr", "de"):
        card_path = out / f"owner_card_{lang}.html"
        card_path.write_text(render_card_document(lang), encoding="utf-8")
        written.append(str(card_path))

    card_model_path = out / "owner_card.json"
    _write(card_model_path, card_json_bytes())
    written.append(str(card_model_path))

    record = empty_capture(bundle, session_id=args.session_id,
                           now=args.now or None)
    session_path = write_session(record, out)
    written.append(str(session_path))

    if not args.no_demo:
        from .demo_page import render_demo_page
        demo_path = out / "harness_demo.html"
        demo_path.write_text(render_demo_page(bundle), encoding="utf-8")
        written.append(str(demo_path))

    summary = {
        "harness": "frontier-human-gate-harness",
        "version": __version__,
        "mode": "fixture",
        "offline": True,
        "fixture": str(Path(args.fixture)),
        "bundle_sha256": sha,
        "query_sha256": query_sha256(bundle),
        "query": bundle.get("query"),
        "n_decisions": len(bundle.get("decisions") or []),
        "n_rows_rendered": len(build_model(bundle)),
        "baseline": render_summary(bundle),
        "capture": {
            "session_id": record["session_id"],
            "status": record["status"],
            "missing_answers": record["missing_answers"],
            "path": str(session_path),
        },
        "written": written,
        "contract_checks": {
            "local_bundle_mirror_errors": mirror_errors,
            "accepted_product_validator_errors": product_errors,
            "accepted_product_validator_available": product_errors is not None,
            "conventional_fields": "present",
        },
    }
    summary_path = out / "summary.json"
    _write(summary_path, (json.dumps(summary, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    written.append(str(summary_path))

    if not args.quiet:
        print(json.dumps({
            "ok": True,
            "mode": "fixture",
            "n_decisions": summary["n_decisions"],
            "bundle_sha256": sha,
            "session_file": str(session_path),
            "written": written,
        }, ensure_ascii=False, indent=2))
    return EXIT_OK


def run_finalize_mode(args: argparse.Namespace) -> int:
    drafts = [read_draft(path) for path in args.finalize]
    bundle = load_bundle(args.fixture) if args.fixture else None
    record = finalize(
        drafts,
        bundle=bundle,
        session_id=args.session_id,
        allow_incomplete=args.allow_incomplete,
        now=args.now or None,
    )
    path = write_session(record, Path(args.out))
    if not args.quiet:
        print(json.dumps({
            "ok": True,
            "mode": "finalize",
            "session_file": str(path),
            "status": record["status"],
            "answers": sorted(record["answers"]),
            "missing_answers": record["missing_answers"],
            "bundle_sha256": record["bundle_sha256"],
            "bundle_hash_status": record["bundle_hash_status"],
            "actions": len(record["actions"]),
            "decisions_opened": len(record["decisions_opened"]),
            "counter_authorities_opened": len(record["counter_authorities_opened"]),
            "wall_clock_seconds": record["wall_clock_seconds"],
        }, ensure_ascii=False, indent=2))
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m frontier_human_gate_harness.cli",
        description="Offline owner test harness for the Master Prompt human product gate.",
    )
    parser.add_argument("--fixture", help="query_result_bundle JSON file")
    parser.add_argument("--out", help="output directory")
    parser.add_argument("--finalize", nargs="+", metavar="DRAFT",
                        help="one or more session draft JSON files to validate and merge")
    parser.add_argument("--session-id", help="explicit session id (never invented for you)")
    parser.add_argument("--allow-incomplete", action="store_true",
                        help="write an explicitly labelled incomplete record instead of "
                             "rejecting missing answers")
    parser.add_argument("--now", help="fixed ISO-8601 Z timestamp for reproducible output")
    parser.add_argument("--no-demo", action="store_true", help="skip harness_demo.html")
    parser.add_argument("--allow-network", action="store_true",
                        help="do not install the offline guard (nothing here needs it)")
    parser.add_argument("--quiet", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.fixture and not args.finalize:
        parser.print_usage(sys.stderr)
        print("error: provide --fixture <bundle> and/or --finalize <draft> [...]", file=sys.stderr)
        return EXIT_USAGE
    if not args.out:
        print("error: --out <dir> is required", file=sys.stderr)
        return EXIT_USAGE

    guard = None
    if not args.allow_network:
        guard = offline_only()
        guard.__enter__()
    try:
        if args.fixture:
            code = run_fixture_mode(args)
            if code != EXIT_OK:
                return code
        if args.finalize:
            return run_finalize_mode(args)
        return EXIT_OK
    except MissingBundleFieldError as exc:
        print(f"3: {exc}", file=sys.stderr)
        return EXIT_BUNDLE_FIELD
    except MissingAnswerError as exc:
        print(f"2: {exc}", file=sys.stderr)
        return EXIT_CAPTURE
    except (CaptureError, BundleError) as exc:
        print(f"2: {exc}", file=sys.stderr)
        return EXIT_CAPTURE
    except NetworkDisabled as exc:
        print(f"2: {exc}", file=sys.stderr)
        return EXIT_CAPTURE
    finally:
        if guard is not None:
            guard.__exit__(None, None, None)


if __name__ == "__main__":
    raise SystemExit(main())
