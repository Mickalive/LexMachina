#!/usr/bin/env python3
"""Bounded audit packet: every claim -> one artifact hash -> one command.

Why this module exists
----------------------
The recurring orchestration failure on this lane is not a product defect: the
team job is green, but the independent audit consumes its whole 2700 s work
quantum before writing a gate (``LEX_WORK_QUANTUM_EXPIRED``, exit 78).  The
snapshot then survives unaudited.  A resumed producer cannot change the audit
budget, but it CAN remove the auditor's discovery cost: publish a small,
machine-readable packet that names each claim, the exact committed artifact
that carries it, that artifact's sha256, and a bounded reproduction command.

The packet is deliberately *not* a verdict.  It contains no ``gate`` /
``safe_to_integrate`` / posture flag, mints nothing, and never writes
``results/audit/**`` or ``reports/audit/**``.  It is evidence for the auditor,
who still has to decide PASS / REVISE / BLOCKED independently.

Design notes
------------
* All numbers are read from committed artifacts, never typed into the packet.
* ``verify_packet()`` is a pure-ish function of the packet plus the working
  tree: it re-hashes artifacts and evaluates declarative assertions.
* Commands are optional (``--run-commands``).  Hash/assertion verification is
  the fast path and takes well under a second.
* ``bounded_seconds`` records the author's measured upper bound for the claim's
  verification; it is not a benchmark claim.

Usage
-----
    python3 product/audit_packet.py --run-id 43198349659 \\
        --resumed-run-id 43189571965 --predecessor-run-id 43180882004 \\
        --write

    python3 product/audit_packet.py \\
        --verify results/product/audit_packet/CYCLE_43198349659.json \\
        --run-commands
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "product-audit-packet/1"
OUT_DIR = ROOT / "results" / "product" / "audit_packet"

#: Keys a producer-owned evidence artifact must never carry.  A packet that
#: gains one of these has stopped being evidence and is rejected.
FORBIDDEN_VERDICT_KEYS = (
    "gate",
    "safe_to_integrate",
    "human_gate_ready",
    "ready_for_owner_session",
    "packet_admitted",
)

CLAIM_CEILING = (
    "Bounded producer evidence only: every claim names a committed artifact, "
    "its sha256 and a reproduction command. The packet is not an audit gate, "
    "writes nothing in the auditor namespace, labels no run accepted or "
    "rejected, scores no frozen bar and makes no live-retrieval, legal or "
    "performance claim."
)


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _dig(obj: Any, dotted: str) -> Any:
    cur = obj
    for part in dotted.split("."):
        if isinstance(cur, list):
            cur = cur[int(part)]
        elif isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            raise KeyError(dotted)
    return cur


def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _claim(claim_id: str, statement: str, artifact: Path, *,
           root: Path, assertions: list[dict[str, Any]] | None = None,
           bounded_seconds: float = 1.0) -> dict[str, Any]:
    return {
        "id": claim_id,
        "statement": statement,
        "artifact": _rel(artifact, root),
        "sha256": _sha256(artifact),
        "bytes": artifact.stat().st_size,
        "assertions": assertions or [],
        "bounded_seconds": bounded_seconds,
    }


def _command(command_id: str, argv: list[str], *, expect_exit: int = 0,
             timeout_s: int = 600, bounded_seconds: float | None = None) -> dict:
    return {
        "id": command_id,
        "argv": argv,
        "expect_exit": expect_exit,
        "timeout_s": timeout_s,
        "bounded_seconds": bounded_seconds,
    }


# --------------------------------------------------------------------------- #
# build
# --------------------------------------------------------------------------- #

def build_packet(*, executing_run_id: int | str, resumed_run_id: int | str,
                 predecessor_run_id: int | str, direction_version: int = 68,
                 root: Path = ROOT) -> dict[str, Any]:
    """Derive a packet from committed artifacts for one resumed snapshot."""
    root = Path(root)
    ex, res, pred = str(executing_run_id), str(resumed_run_id), str(predecessor_run_id)

    raw_path = root / "results" / "product" / "orchestration" \
        / f"CYCLE_{res}_run_jobs_raw.json"
    diag_path = root / "results" / "product" / "orchestration" \
        / f"CYCLE_{res}_resume_diagnosis.json"
    inherited_report = root / "reports" / "product" / f"CYCLE_{res}.md"
    pre_diag = root / "results" / "product" / "orchestration" \
        / f"CYCLE_{pred}_resume_diagnosis.json"
    pre_raw = root / "results" / "product" / "orchestration" \
        / f"CYCLE_{pred}_run_jobs_raw.json"
    slice_dir = root / "results" / "product" / "vertical_slice" / f"CYCLE_{res}"
    slice_summary = slice_dir / "summary.json"
    slice_bundle = slice_dir / "rent-default.bundle.json"
    snapshot_results = root / "results" / "product" \
        / "vertical_slice_results_20261112T160000Z.json"
    before_bundle = root / "results" / "product" / "offline_slice" \
        / "20261024T142517Z" / "rent-default.bundle.json"
    after_bundle = root / "results" / "product" / "offline_slice" \
        / "20261025T070356Z" / "rent-default.bundle.json"

    diag = _load(diag_path)
    raw = _load(raw_path)

    claims: list[dict[str, Any]] = []

    claims.append(_claim(
        "orchestration_diagnosis",
        f"Run {res}'s team job was green and its audit step failed on the "
        f"2700 s work quantum (exit 78) with no gate; the run is "
        f"UNADJUDICATED and its snapshot carries a committed delta.",
        diag_path, root=root, bounded_seconds=0.2, assertions=[
            {"kind": "equals", "path": "run_id", "value": res},
            {"kind": "equals", "path": "predecessor_run_id", "value": pred},
            {"kind": "equals", "path": "orchestration.classification",
             "value": "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE"},
            {"kind": "equals", "path": "orchestration.team.conclusion",
             "value": "success"},
            {"kind": "equals", "path": "orchestration.audit.failed_step",
             "value": "Independent audit"},
            {"kind": "truthy", "path": "orchestration.mechanism.quantum_expired"},
            {"kind": "equals", "path": "orchestration.mechanism.exit_code",
             "value": 78},
            {"kind": "not_truthy",
             "path": "orchestration.audit.gate_file_written"},
            {"kind": "equals", "path": "adjudication.status",
             "value": "UNADJUDICATED"},
            {"kind": "equals", "path": "durable_delta.classification",
             "value": "COMMITTED_DELTA"},
        ]))

    claims.append(_claim(
        "public_run_record",
        f"The committed run/jobs snapshot was fetched by this executing run "
        f"{ex} and carries the public LEX_WORK_QUANTUM_EXPIRED annotation for "
        f"run {res}'s audit job.",
        raw_path, root=root, bounded_seconds=0.2, assertions=[
            {"kind": "equals", "path": "schema",
             "value": "product-run-jobs-raw/2"},
            {"kind": "equals", "path": "run.id", "value": int(res)},
            {"kind": "equals", "path": "fetched_by_run", "value": int(ex)},
            {"kind": "annotations_contain",
             "value": "LEX_WORK_QUANTUM_EXPIRED seconds=2700"},
        ]))

    claims.append(_claim(
        "predecessor_diagnosis",
        f"The predecessor run {pred} has its own committed diagnosis, so "
        f"this resume does not re-derive the earlier chain.",
        pre_diag, root=root, bounded_seconds=0.2, assertions=[
            {"kind": "equals", "path": "run_id", "value": pred},
            {"kind": "equals", "path": "durable_delta.classification",
             "value": "COMMITTED_DELTA"},
            {"kind": "truthy",
             "path": "orchestration.mechanism.quantum_expired"},
        ]))

    claims.append(_claim(
        "predecessor_run_record",
        f"The predecessor's public run/jobs snapshot is preserved byte-for-byte "
        f"as the input of its diagnosis.",
        pre_raw, root=root, bounded_seconds=0.2, assertions=[
            {"kind": "equals", "path": "run.id", "value": int(pred)},
        ]))

    claims.append(_claim(
        "inherited_report",
        f"The inherited snapshot's report of record exists unchanged; this "
        f"resume publishes its own report rather than editing it.",
        inherited_report, root=root, bounded_seconds=0.2, assertions=[
            {"kind": "contains", "path": "__text__",
             "value": "OFFLINE WIRING EVIDENCE ONLY"},
        ]))

    if slice_summary.is_file():
        claims.append(_claim(
            "inherited_run_scoped_slice",
            f"The inherited snapshot's run-scoped offline slice remains a "
            f"verified full-loop artifact (page contract PASS, network none, "
            f"120 decisions, 8 clusters, all rows clickable).",
            slice_summary, root=root, bounded_seconds=0.2, assertions=[
                {"kind": "truthy", "path": "verified"},
                {"kind": "equals", "path": "mode", "value": "full_loop"},
                {"kind": "truthy", "path": "page_contract"},
                {"kind": "equals", "path": "stats.n_decisions", "value": 120},
                {"kind": "equals", "path": "stats.n_clusters", "value": 8},
                {"kind": "equals", "path": "stats.rows_with_xy", "value": 120},
                {"kind": "equals", "path": "stats.rows_with_cluster_id",
                 "value": 120},
                {"kind": "equals", "path": "stats.rows_with_canonical_url",
                 "value": 120},
                {"kind": "equals", "path": "stats.fixture_replay.network",
                 "value": "none"},
                {"kind": "equals", "path": "stats.adapter_transport_attempts",
                 "value": 0},
            ]))
    if slice_bundle.is_file():
        claims.append(_claim(
            "inherited_slice_bundle",
            "The inherited run-scoped bundle carries the routed span seam and "
            "an answer whose citations are all present in the mapped set.",
            slice_bundle, root=root, bounded_seconds=0.4, assertions=[
                {"kind": "truthy",
                 "path": "provenance.counter_evidence_span.applied"},
            ]))

    if snapshot_results.is_file():
        claims.append(_claim(
            "inherited_vertical_slice_result",
            "The snapshot's own vertical-slice result artifact records 120 "
            "decisions, 8 clusters and the counter-status distribution that "
            "product/tests/test_cycle_43198349659.py re-derives under a "
            "socket trap.",
            snapshot_results, root=root, bounded_seconds=0.2, assertions=[
                {"kind": "equals", "path": "n_decisions", "value": 120},
                {"kind": "equals", "path": "n_clusters", "value": 8},
                {"kind": "equals", "path": "counter_status_dist.cited",
                 "value": 2},
                {"kind": "equals",
                 "path": "counter_status_dist.candidate-limiting", "value": 4},
                {"kind": "equals", "path": "content_coverage.by_state.full_text",
                 "value": 25},
            ]))

    for label, path in (("v68_before_bundle", before_bundle),
                        ("v68_after_bundle", after_bundle)):
        if path.is_file():
            claims.append(_claim(
                label,
                "Accepted v68 before/after evidence for the rejection/incumbent "
                "leg; consumed REPORTED-ONLY and never re-derived here.",
                path, root=root, bounded_seconds=0.4, assertions=[]))

    # Absence claims: this producer must not write the auditor namespace.
    claims.append({
        "id": "audit_namespace_untouched",
        "statement": "This producer wrote no auditor-namespace path and minted "
                     "no gate; the /audit half of requirement 4 is the "
                     "independent auditor's to create.",
        "artifact": None,
        "sha256": None,
        "bytes": None,
        "assertions": [
            {"kind": "absent_path",
             "value": f"results/audit/product/CYCLE_{ex}_GATE.json"},
            {"kind": "absent_path",
             "value": f"reports/audit/product/CYCLE_{ex}.md"},
        ],
        "bounded_seconds": 0.1,
    })

    commands = [
        _command(
            "state_contract",
            ["python3", "product/state_contract.py", "--check",
             "--direction-version", str(direction_version), "--json"],
            expect_exit=0, timeout_s=180, bounded_seconds=2.0),
        _command(
            "cycle_reproduction",
            ["python3", "-m", "pytest",
             f"product/tests/test_cycle_{ex}.py", "-q"],
            expect_exit=0, timeout_s=600, bounded_seconds=60.0),
    ]

    packet = {
        "schema": SCHEMA,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "executing_run_id": ex,
        "resumed_run_id": res,
        "predecessor_run_id": pred,
        "direction_version": direction_version,
        "claim_ceiling": CLAIM_CEILING,
        "forbidden_verdict_keys_present": [],
        "claims": claims,
        "commands": commands,
        "bounded_total_seconds": round(
            sum(float(c.get("bounded_seconds") or 0) for c in claims)
            + sum(float(c.get("bounded_seconds") or 0) for c in commands), 2),
        "audit_entrypoint": (
            "python3 product/audit_packet.py --verify "
            f"{_rel(OUT_DIR / f'CYCLE_{ex}.json', root)} --run-commands"
        ),
    }
    packet["forbidden_verdict_keys_present"] = [
        k for k in FORBIDDEN_VERDICT_KEYS if k in packet]
    return packet


# --------------------------------------------------------------------------- #
# verify
# --------------------------------------------------------------------------- #

def _artifact_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:  # pragma: no cover - no binary claims by design
        return ""


def _check_assertion(assertion: dict[str, Any], *, root: Path,
                     payload: Any | None, artifact: Path | None) -> str | None:
    kind = assertion.get("kind")
    path = assertion.get("path")
    value = assertion.get("value")

    if kind == "absent_path":
        target = root / str(value)
        return None if not target.exists() else f"path exists: {value}"
    if kind == "annotations_contain":
        blocks = (payload or {}).get("check_run_annotations_by_job_id") or {}
        messages: list[str] = []
        for block in blocks.values():
            if isinstance(block, dict):
                messages.extend(str(m) for m in (block.get("annotations") or []))
        return None if any(str(value) in m for m in messages) else (
            f"annotation missing: {value!r}")
    if kind == "contains" and path == "__text__":
        text = _artifact_text(artifact) if artifact is not None else ""
        return None if str(value) in text else f"text missing: {value!r}"
    if payload is None:
        return "no artifact payload"
    try:
        got = _dig(payload, str(path))
    except (KeyError, IndexError, ValueError, TypeError):
        return f"path missing: {path}"

    if kind == "equals":
        return None if got == value else f"{path}={got!r} != {value!r}"
    if kind == "truthy":
        return None if bool(got) else f"{path} is falsy"
    if kind == "not_truthy":
        return None if not bool(got) else f"{path} is truthy"
    if kind == "contains":
        if isinstance(got, str):
            return None if str(value) in got else f"{path} missing {value!r}"
        if isinstance(got, (list, tuple, set)):
            return None if value in got else f"{path} missing {value!r}"
        return f"{path} is not containable"
    if kind == "ge":
        return None if got is not None and got >= value else f"{path}={got!r} < {value!r}"
    if kind == "le":
        return None if got is not None and got <= value else f"{path}={got!r} > {value!r}"
    return f"unknown assertion kind: {kind!r}"


def verify_packet(packet: dict[str, Any], *, root: Path = ROOT,
                  run_commands: bool = False) -> dict[str, Any]:
    """Re-hash and re-assert every claim; optionally run the bounded commands."""
    root = Path(root)
    started = time.monotonic()
    failures: list[dict[str, Any]] = []
    checked = 0

    if packet.get("schema") != SCHEMA:
        failures.append({"claim": "<schema>",
                         "problem": f"schema={packet.get('schema')!r}"})
    for key in FORBIDDEN_VERDICT_KEYS:
        if key in packet:
            failures.append({"claim": "<packet>",
                             "problem": f"forbidden verdict key: {key}"})

    for claim in packet.get("claims") or []:
        checked += 1
        artifact = claim.get("artifact")
        payload = None
        artifact_path = None
        if artifact is not None:
            artifact_path = root / str(artifact)
            if not artifact_path.is_file():
                failures.append({"claim": claim.get("id"),
                                 "problem": f"artifact missing: {artifact}"})
                continue
            got_sha = _sha256(artifact_path)
            if got_sha != claim.get("sha256"):
                failures.append({"claim": claim.get("id"),
                                 "problem": f"sha256 {got_sha} != "
                                            f"{claim.get('sha256')}"})
                continue
            if str(artifact).endswith(".json"):
                try:
                    payload = _load(artifact_path)
                except json.JSONDecodeError as exc:
                    failures.append({"claim": claim.get("id"),
                                     "problem": f"invalid JSON: {exc}"})
                    continue
        for assertion in claim.get("assertions") or []:
            problem = _check_assertion(assertion, root=root, payload=payload,
                                      artifact=artifact_path)
            if problem:
                failures.append({"claim": claim.get("id"), "problem": problem})

    command_results: list[dict[str, Any]] = []
    if run_commands:
        for command in packet.get("commands") or []:
            started_cmd = time.monotonic()
            try:
                proc = subprocess.run(
                    command["argv"], cwd=str(root), capture_output=True,
                    text=True, timeout=int(command.get("timeout_s") or 600),
                    check=False)
                code = proc.returncode
                tail = (proc.stdout or "")[-2000:] + (proc.stderr or "")[-2000:]
                timed_out = False
            except subprocess.TimeoutExpired as exc:
                code = None
                tail = "timeout"
                timed_out = True
            ok = (not timed_out) and code == command.get("expect_exit", 0)
            command_results.append({
                "id": command.get("id"),
                "exit_code": code,
                "expected": command.get("expect_exit", 0),
                "timed_out": timed_out,
                "seconds": round(time.monotonic() - started_cmd, 3),
                "ok": ok,
                "tail": tail[-1000:],
            })
            if not ok:
                failures.append({"claim": f"command:{command.get('id')}",
                                 "problem": f"exit {code}, expected "
                                            f"{command.get('expect_exit', 0)}"})

    return {
        "schema": "product-audit-packet-verification/1",
        "packet_schema": packet.get("schema"),
        "executing_run_id": packet.get("executing_run_id"),
        "resumed_run_id": packet.get("resumed_run_id"),
        "status": "PASS" if not failures else "FAIL",
        "claims_checked": checked,
        "claims_failed": len({f["claim"] for f in failures}),
        "commands_run": command_results,
        "failures": failures,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "claim_ceiling": (
            "Verification of producer evidence only. A PASS here is not an "
            "audit gate, does not label the run accepted and moves no frozen "
            "bar."),
    }


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-id", help="executing (current) run id")
    ap.add_argument("--resumed-run-id", help="persisted snapshot run id")
    ap.add_argument("--predecessor-run-id", help="snapshot's predecessor run id")
    ap.add_argument("--direction-version", type=int, default=68)
    ap.add_argument("--out", help="packet output path")
    ap.add_argument("--write", action="store_true",
                    help="write the generated packet to --out")
    ap.add_argument("--verify", help="verify an existing packet path")
    ap.add_argument("--run-commands", action="store_true",
                    help="also run the packet's bounded reproduction commands")
    ap.add_argument("--json", action="store_true", help="print JSON")
    args = ap.parse_args(argv)

    if args.verify:
        packet = _load(Path(args.verify))
        result = verify_packet(packet, run_commands=args.run_commands)
        print(json.dumps(result, indent=2) if args.json
              else f"audit packet: {result['status']} "
                   f"({result['claims_checked']} claims, "
                   f"{len(result['failures'])} failures, "
                   f"{result['elapsed_seconds']} s)")
        return 0 if result["status"] == "PASS" else 1

    if not (args.run_id and args.resumed_run_id and args.predecessor_run_id):
        ap.error("--run-id, --resumed-run-id and --predecessor-run-id are required")
    packet = build_packet(
        executing_run_id=args.run_id,
        resumed_run_id=args.resumed_run_id,
        predecessor_run_id=args.predecessor_run_id,
        direction_version=args.direction_version,
    )
    out = Path(args.out) if args.out else OUT_DIR / f"CYCLE_{args.run_id}.json"
    if args.write:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n",
                       encoding="utf-8")
    result = verify_packet(packet)
    summary = {
        "out": str(out) if args.write else None,
        "status": result["status"],
        "claims": len(packet["claims"]),
        "failures": result["failures"],
        "bounded_total_seconds": packet["bounded_total_seconds"],
    }
    print(json.dumps(summary, indent=2) if args.json else summary)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
