#!/usr/bin/env python3
"""The multi-query comparative human-gate packet (factory direction v52, item 3).

Why this exists
---------------
The shipped path was **one query per owner ceremony**: the owner opens the page,
runs a question, works it, exports one session. Master Prompt §12 asks the human
gate to be answered on *"a SMALL SET of real legal research tasks"*, and a single
question cannot tell the difference between "this map helped me" and "this map
happened to help me on this question".

So this tool builds the packet the gate needs, without ever producing the
evidence a jurist has to produce:

    3 pre-registered real questions (FR / DE / IT)
      -> each run through the shipped product server (query -> retrieval/cache
         -> query_result_bundle -> sourced answer -> counter-authority pass)
      -> each bundle RE-VERIFIED at run time by product/query/gate_admissibility.py
      -> each question emitted as a per-query draft: binding, disclosures, deep
         link, and the exact finalize command - never as a session record
      -> the existing human_gate_session guards exercised for every bundle, so
         the ceremony is known to work before the owner is asked to sit down

What it never does
------------------
* It never answers a gate question and never writes ``human_gate_ready``.
* It never writes a session record into any evidence directory. The guard probe
  writes only into a throwaway temp directory, labelled SIMULATED, and the
  owner-facing path is the browser export -> ``human_gate_session.py finalize``.
* It never ships a bundle that fails the run-time admissibility check, and it
  never reuses a bundle from an earlier run: every question is retrieved now.
* It never edits the pre-registration. ``product/data/gate_packet_questions.json``
  is pinned by digest; changing a question after seeing what retrieval returned
  is refused, because the questions must be fixed BEFORE the results.

Commands
--------
    # retrieve + verify all three questions now, write the packet
    python product/gate_packet.py preflight --live --run-id <run> --operator <name>

    # offline machinery rehearsal against the deterministic fixture corpus
    python product/gate_packet.py preflight --fixture --run-id rehearsal

    # re-verify a packet's bundles at run time and print the owner ceremony
    python product/gate_packet.py card --packet results/product/gate_packet/<run> --serve

    # machine-readable re-verification only
    python product/gate_packet.py verify --packet results/product/gate_packet/<run>

Exit codes: 0 ready, 2 bad arguments / edited pre-registration, 4 node export
driver unavailable, 5 at least one question is blocked (not admissible), 6 I/O,
9 no packet found.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
import tempfile
import threading
import time
import urllib.parse
from pathlib import Path
from typing import Any

PRODUCT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PRODUCT_ROOT.parent
for _p in (str(PRODUCT_ROOT), str(REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import human_gate_evidence  # noqa: E402
import human_gate_finalize as hgf  # noqa: E402
import human_gate_session as runner  # noqa: E402
from gate_rehearsal import free_port, http_json, _wait_health  # noqa: E402  (existing shell helpers)

from product.query.gate_admissibility import verify_bundle  # noqa: E402
from product.replay_bundle import content_sha256  # noqa: E402

QUESTIONS_PATH = PRODUCT_ROOT / "data" / "gate_packet_questions.json"

#: Digest of the pre-registered question set, frozen in the same commit that
#: froze the questions.  A mismatch means the questions were edited after
#: pre-registration, which invalidates the packet: pick new questions, bump
#: ``packet_id``, and update this constant deliberately.
PREREGISTERED_MANIFEST_SHA256 = "32eace355b70edc6a8dcc6cca97ec745b1a1c8985a7afd13668fa752008d34cb"

DEFAULT_OUT_ROOT = REPO_ROOT / "results" / "product" / "gate_packet"

CLAIM_CEILING = (
    "GATE PACKET MATERIAL, NOT GATE EVIDENCE: this packet pre-registers the questions, "
    "re-verifies their bundles and prepares the ceremony. It contains no jurist answer and "
    "no session record; human_gate_ready stays false until real owner/jurist sessions are "
    "finalized through product/human_gate_session.py and read by the director."
)

FIXTURE_CLAIM_CEILING = (
    "MACHINERY REHEARSAL ONLY (fixture corpus): every check, guard and artifact of the gate "
    "packet ran end to end, but the bundles came from the deterministic offline fixture, not "
    "from live OpenCaseLaw. This packet is NOT gate material."
)


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_manifest(path: Path | None = None, *, strict: bool = True) -> dict:
    """Load the pre-registered question set and check it against its pinned digest.

    ``strict`` pins the canonical manifest by digest. An alternate manifest
    (passed explicitly by a caller, e.g. the offline machinery manifest in
    ``product/tests/fixtures``) is not pinned here: its digest is recorded in the
    packet instead, and it can never become gate material because
    ``preflight`` only reports live packets as owner-ready.
    """
    path = Path(path) if path is not None else QUESTIONS_PATH
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    manifest = json.loads(raw.decode("utf-8"))
    if strict and path == QUESTIONS_PATH and digest != PREREGISTERED_MANIFEST_SHA256:
        raise ValueError(
            f"pre-registration digest mismatch for {path}: {digest} != {PREREGISTERED_MANIFEST_SHA256}. "
            "The questions must be fixed before the results; if they really must change, give the "
            "packet a new packet_id and update PREREGISTERED_MANIFEST_SHA256 in the same commit."
        )
    manifest["_sha256"] = digest
    manifest["_path"] = str(path)
    return manifest


def packet_dir(args: argparse.Namespace) -> Path:
    if getattr(args, "packet", None):
        return Path(args.packet)
    root = Path(args.out_root) if getattr(args, "out_root", None) else DEFAULT_OUT_ROOT
    stamp = (args.run_id if getattr(args, "run_id", None) else dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    return root / str(stamp)


# --------------------------------------------------------------------------- #
# the per-question draft
# --------------------------------------------------------------------------- #
def build_question_draft(
    question: dict,
    bundle: dict,
    verdict: dict,
    *,
    manifest: dict,
    server_run_id: str,
    bundle_path: Path,
    mode: str,
    base_url: str | None,
    top_n: int,
) -> dict:
    """The per-query artifact the owner works from. Deliberately not a session.

    It is *not* a ``lex_human_gate_session`` draft on purpose: a session draft
    with no recorded interaction is refused by ``human_gate_finalize`` (exit 4)
    and one with invented interactions would be fabricated evidence. This file
    therefore binds the question to the exact bundle, carries the disclosures
    the jurist needs, and states the one command that turns the browser export
    into a session record.
    """
    query = bundle.get("query")
    # The link the packet ships carries the QUESTION, not a run id: a preflight
    # run id only resolves inside the server process that produced it, and a
    # link to a dead run would be worse than no link.  The ceremony re-seeds the
    # verified bundle into the served app and links that run instead (see
    # seed_runs / owner_card), so the jurist works the artifact that was checked.
    link_query = urllib.parse.urlencode({"q": query, "n": top_n})
    finalize = (
        "python product/human_gate_session.py finalize <exported draft.json> "
        f"--bundle {bundle_path} "
        f"--run-id {manifest.get('_run_id', '<run-id>')} "
        f"--operator {manifest.get('_operator', '<operator>')} --owner-session"
    )
    return {
        "record_type": "product-gate-packet-question",
        "is_session_draft": False,
        "schema": "product-gate-packet-question/1",
        "packet_id": manifest.get("packet_id"),
        "pre_registered_at": manifest.get("preregistered_at"),
        "manifest_sha256": manifest.get("_sha256"),
        "recorded_at": _now(),
        "mode": mode,
        "qid": question.get("qid"),
        "language": question.get("language"),
        "legal_area": question.get("legal_area"),
        "question": query,
        "hypothesis": question.get("hypothesis"),
        "look_for": question.get("look_for"),
        "counter_authority_needed": question.get("counter_authority_needed"),
        "why_this_question": question.get("why_this_question"),
        "server_run_id": server_run_id,
        "bundle": {
            "path": str(bundle_path),
            "content_sha256": content_sha256(bundle),
            "canonical_sha256": hgf.canonical_sha256(bundle),
            "n_decisions": verdict["measured"].get("n_decisions"),
            "n_clusters": verdict["measured"].get("n_clusters"),
            "n_counter_authorities": verdict["measured"].get("n_counter_authorities"),
        },
        "admissibility": {
            "admissible": verdict["admissible"],
            "blocking_count": verdict["blocking_count"],
            "warning_count": verdict["warning_count"],
            "findings": verdict["findings"],
            "measured": verdict["measured"],
        },
        "deep_link": f"{base_url or 'http://127.0.0.1:8791'}/?{link_query}" if base_url else None,
        "gate_questions": hgf.GATE_QUESTIONS,
        "success_rule": manifest.get("success_rule"),
        "how_to_answer": [
            "open the deep link (the query and the run are already filled in)",
            "work the MAP first, then switch to LIST and work the same case again",
            "open the decisions and the counter authorities in both views",
            "answer the four questions in the sidebar answer card",
            'press "Exporter la session"',
            f"then: {finalize}",
        ],
        "finalize_command": finalize,
        "guard": (
            "this file is not a session draft: human_gate_finalize.validate_draft refuses it "
            "(exit 4). Only a draft exported from the browser after the real session can become "
            "a session record."
        ),
        "claim_ceiling": CLAIM_CEILING,
    }


# --------------------------------------------------------------------------- #
# the guards: does the owner ceremony actually work for THIS bundle?
# --------------------------------------------------------------------------- #
def _probe_session_draft(bundle: dict) -> dict:
    """A structurally valid, deliberately EMPTY session draft for this bundle.

    Used only to exercise the finalizer's machinery (never written to an
    evidence directory as an owner record): it opens nothing and switches
    nothing, because inventing those would be fabricating a jurist's behaviour.
    """
    query = bundle.get("query")
    return {
        "record_type": "lex_human_gate_session",
        "team_id": "frontier-human-gate-harness",
        "session_id_origin": "gate_packet_probe",
        "query": query,
        "started_at": "2026-01-01T00:00:00Z",
        "ended_at": "2026-01-01T00:00:01Z",
        "view_mode_initial": "map",
        "view_mode_final": "map",
        "actions": [{"event": "probe", "view_mode": "map"}],
        "decisions_opened": [],
        "counter_authorities_opened": [],
        "bundle_ref": {"query": query, "n_decisions": len(bundle.get("decisions") or [])},
    }


def probe_guards(bundle: dict, question_file: dict, *, run_id: str, operator: str) -> dict:
    """Exercise the existing human-gate guards against this bundle, writing nothing.

    Returns the exit codes the owner will actually see, so the ceremony is not
    discovered to be broken after the owner has already spent a sitting on it.
    """
    out: dict[str, Any] = {"run_id": run_id, "operator": operator, "writes": "temp directory only"}

    # 1. the packet question file must never be finalizable as evidence.
    problems = hgf.validate_draft(question_file)
    out["packet_file_refused"] = {
        "exit_code": 4 if problems else None,
        "ok": bool(problems),
        "problems": problems[:4],
    }

    # 2. a machine probe against this bundle: simulated, incomplete, temp dir.
    draft = _probe_session_draft(bundle)
    with tempfile.TemporaryDirectory(prefix="lex_gate_packet_probe_") as tmp:
        tmp_dir = Path(tmp) / "simulated"
        try:
            record = hgf.finalize(draft, None, bundle, run_id=run_id, finalized_by=operator,
                                  simulated=True, session_id="packet-probe")
            code, written = 0, None
        except hgf.IncompleteSession as incomplete:
            record, code, written = incomplete.record, incomplete.exit_code, None
        except hgf.FinalizeError as exc:  # pragma: no cover - would be a real defect
            return {"ok": False, "error": f"{exc} (exit {exc.exit_code})"}
        if code == 0:  # pragma: no cover - impossible without answers
            written = hgf.write_record(record, tmp_dir)
        elif written is None:
            written = hgf.write_record(record, tmp_dir)
        scan = human_gate_evidence.scan([tmp_dir])
        out["simulated_probe"] = {
            "exit_code": code,
            "ok": code in (0, 3) and scan["admissible"],
            "record_status": record.get("status"),
            "simulated": record.get("simulated"),
            "bundle_hash_status": record.get("bundle_hash_status"),
            "evidence_scan_admissible": scan["admissible"],
            "written_to": "temp directory (deleted with it)",
        }

    # 3. negative control: a simulated record may never enter the canonical dir.
    sim_record = dict(record)
    sim_record["owner_session_confirmed"] = False
    sim_problems = hgf.record_admissibility_problems(sim_record, hgf.DEFAULT_OUT_DIR)
    out["simulated_into_canonical_refused"] = {
        "exit_code": 8 if sim_problems else None,
        "ok": bool(sim_problems),
        "problems": sim_problems[:2],
    }

    # 4. negative control: no declaration, no canonical write either.
    real_record = dict(sim_record)
    real_record.update({
        "simulated": False,
        "claim_ceiling": hgf.CLAIM_CEILING_REAL,
        "owner_session_confirmed": False,
        "answers": {qid: {"rating": "yes", "note": "probe"} for qid in hgf.GATE_QUESTIONS},
        "missing_answers": [],
    })
    real_problems = hgf.record_admissibility_problems(real_record, hgf.DEFAULT_OUT_DIR)
    out["undeclared_into_canonical_refused"] = {
        "exit_code": 8 if real_problems else None,
        "ok": bool(real_problems),
        "problems": real_problems[:2],
    }

    # 5. the positive control: a REAL, answered, declared session on THIS bundle
    #    would be accepted into the canonical directory. Never written anywhere.
    real_record["owner_session_confirmed"] = True
    real_record["wall_clock_probe"] = True
    real_record["session_metrics"] = {**(record.get("session_metrics") or {}), "wall_clock_seconds": 1.0}
    real_problems = hgf.record_admissibility_problems(real_record, hgf.DEFAULT_OUT_DIR) + \
        hgf.validate_real_session(real_record)
    out["real_session_would_be_accepted"] = {
        "ok": not real_problems,
        "exit_code": 0 if not real_problems else 7,
        "problems": real_problems[:3],
        "note": "in-memory check only; no record was written",
    }

    out["ok"] = all([
        out["packet_file_refused"]["ok"],
        out["simulated_probe"]["ok"],
        out["simulated_into_canonical_refused"]["ok"],
        out["undeclared_into_canonical_refused"]["ok"],
        out["real_session_would_be_accepted"]["ok"],
    ])
    return out


# --------------------------------------------------------------------------- #
# preflight
# --------------------------------------------------------------------------- #
def _run_one_query(base: str, question: dict, *, top_n: int, wait_s: float, stage_timeout_s: float) -> tuple[dict, dict]:
    """Drive one question through the shipped three-stage job API. Returns (bundle, timing)."""
    t0 = time.time()
    first, _ = http_json(
        f"{base}/api/query/start?" + urllib.parse.urlencode({"q": question["question"], "n": top_n}),
        timeout=stage_timeout_s,
    )
    server_run_id = first["run_id"]
    stage = {"start_s": round(time.time() - t0, 4), "first_page_decisions": len(first["bundle"]["decisions"])}
    t1 = time.time()
    exp, _ = http_json(
        f"{base}/api/query/expand?" + urllib.parse.urlencode({"run_id": server_run_id, "wait_s": wait_s}),
        timeout=wait_s + 60,
    )
    stage["expand_s"] = round(time.time() - t1, 4)
    stage["expand_job"] = (exp.get("job") or {}).get("status")
    t2 = time.time()
    enr, _ = http_json(
        f"{base}/api/query/enrich?" + urllib.parse.urlencode({"run_id": server_run_id, "wait_s": wait_s}),
        timeout=wait_s + 60,
    )
    stage["enrich_s"] = round(time.time() - t2, 4)
    stage["enrich_job"] = (enr.get("job") or {}).get("status") or enr.get("status")
    stage["total_s"] = round(time.time() - t0, 4)
    bundle_resp, _ = http_json(
        f"{base}/api/query/bundle?" + urllib.parse.urlencode({"run_id": server_run_id}), timeout=60
    )
    bundle = bundle_resp["bundle"]
    if not bundle.get("query"):
        bundle["query"] = question["question"]
    return bundle, {"stages": stage, "server_run_id": server_run_id}


def finalize_summary(summary: dict, n_questions: int, mode: str) -> dict:
    """Roll per-question outcomes up into the packet verdict.

    Extracted so the ordering is testable: the previous inline version read
    ``summary["guards_all_ok"]`` while computing ``ready_for_owner_session`` and
    only wrote it afterwards.  Python short-circuits, so that only raised when
    ``ok`` was true AND the mode was live - i.e. exactly the run the ceremony
    needs (live run 38812599575 reached 3/3 admissible and died on the
    KeyError, losing the whole packet).
    """
    done = [q for q in summary["questions"] if q["status"] != "pending"]
    summary["n_questions"] = n_questions
    summary["n_attempted"] = len(done)
    summary["blocked"] = [q["qid"] for q in done if q["status"] == "blocked"]
    summary["admissible_questions"] = [q["qid"] for q in done if q["status"] == "admissible"]
    summary["ok"] = bool(done) and not summary["blocked"] and len(done) == n_questions
    summary["guards_all_ok"] = all(q.get("guards_ok") for q in done)
    summary["ready_for_owner_session"] = bool(
        summary["ok"] and mode == "live" and summary["guards_all_ok"]
    )
    if mode == "fixture":
        summary["ready_for_owner_session"] = False
        summary["fixture_note"] = FIXTURE_CLAIM_CEILING
    return summary


def preflight(args: argparse.Namespace) -> tuple[int, dict]:
    from query_app import make_server  # local import: only the runner needs the server

    try:
        manifest = load_manifest(Path(args.questions) if args.questions else QUESTIONS_PATH)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return 2, {"ok": False, "error": str(exc)}
    manifest["_run_id"] = args.run_id
    manifest["_operator"] = args.operator

    mode = "fixture" if args.fixture else "live"
    out = packet_dir(args)
    (out / "questions").mkdir(parents=True, exist_ok=True)
    # The packet carries its own copy of the manifest it was built from: a later
    # edit of the canonical file must not silently re-point a shipped packet at
    # different questions, and re-verification must use the frozen copy.
    manifest_copy = out / "manifest.json"
    manifest_copy.write_text(
        json.dumps({k: v for k, v in manifest.items() if not k.startswith("_")}, indent=2,
                   ensure_ascii=False) + "\n", encoding="utf-8")
    manifest_copy_sha256 = hashlib.sha256(manifest_copy.read_bytes()).hexdigest()
    port = args.port or free_port()
    base = f"http://127.0.0.1:{port}"

    summary: dict[str, Any] = {
        "record_type": "lex_gate_packet_preflight",
        "schema": "product-gate-packet/1",
        "packet_id": manifest["packet_id"],
        "packet_dir": str(out),
        "generated_at": _now(),
        "mode": mode,
        "run_id": args.run_id,
        "operator": args.operator,
        "manifest_sha256": manifest_copy_sha256,
        "source_manifest_sha256": manifest["_sha256"],
        "source_manifest_path": manifest["_path"],
        "preregistered_at": manifest["preregistered_at"],
        "top_n": args.top_n,
        "base_url": base,
        "success_rule": manifest.get("success_rule"),
        "claim_ceiling": FIXTURE_CLAIM_CEILING if mode == "fixture" else CLAIM_CEILING,
        "questions": [],
        "ok": False,
    }

    srv = make_server("127.0.0.1", port, fixture_mode=(mode == "fixture"), verbose=not args.quiet)
    thread = threading.Thread(target=srv.serve_forever, name="lex-packet-server", daemon=True)
    thread.start()
    try:
        _wait_health(base)
        for index, question in enumerate(manifest["questions"], start=1):
            entry: dict[str, Any] = {
                "index": index,
                "qid": question.get("qid"),
                "language": question.get("language"),
                "question": question.get("question"),
                "status": "pending",
            }
            try:
                bundle, timing = _run_one_query(base, question, top_n=args.top_n,
                                                wait_s=args.wait_s, stage_timeout_s=args.stage_timeout_s)
            except Exception as exc:
                entry.update({"status": "blocked", "error": f"retrieval failed: {type(exc).__name__}: {exc}"})
                summary["questions"].append(entry)
                if not args.keep_going:
                    break
                continue

            bundle_path = out / "questions" / f"{question['qid']}.bundle.json"
            bundle_path.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
            verdict = verify_bundle(
                bundle, question=question, min_decisions=args.min_decisions,
                max_decisions=args.max_decisions,
            )
            verdict["verified_at"] = _now()
            qfile = build_question_draft(
                question, bundle, verdict, manifest=manifest,
                server_run_id=timing["server_run_id"], bundle_path=bundle_path,
                mode=mode, base_url=base, top_n=args.top_n,
            )
            guards = probe_guards(bundle, qfile, run_id=args.run_id, operator=args.operator)
            qfile["guards"] = guards
            (out / "questions" / f"{question['qid']}.question.json").write_text(
                json.dumps(qfile, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )
            (out / "questions" / f"{question['qid']}.admissibility.json").write_text(
                json.dumps(verdict, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )

            blocked = [f for f in verdict["findings"] if f["severity"] == "blocking"]
            entry.update({
                "status": "admissible" if (verdict["admissible"] and guards.get("ok")) else "blocked",
                "server_run_id": timing["server_run_id"],
                "timing": timing["stages"],
                "bundle_path": str(bundle_path),
                "question_path": str(out / "questions" / f"{question['qid']}.question.json"),
                "deep_link": qfile["deep_link"],
                "measured": verdict["measured"],
                "blocking": blocked,
                "warnings": [f for f in verdict["findings"] if f["severity"] == "warning"],
                "notices": [f for f in verdict["findings"] if f["severity"] == "info"],
                "guards_ok": guards.get("ok"),
            })
            summary["questions"].append(entry)
            if not args.quiet:
                print(f"[{index}/{len(manifest['questions'])}] {entry['qid']}: {entry['status']} "
                      f"({entry['measured']['n_decisions']} decisions, "
                      f"{entry['measured']['n_counter_authorities']} counter, "
                      f"{entry['timing']['total_s']}s)")
            if entry["status"] == "blocked" and not args.keep_going:
                break
    finally:
        srv.shutdown()
        srv.server_close()

    summary = finalize_summary(summary, len(manifest["questions"]), mode)
    (out / "packet.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return (0 if summary["ok"] else 5), summary


# --------------------------------------------------------------------------- #
# re-verification + the owner card
# --------------------------------------------------------------------------- #
def _resolve_artifact(raw: str, packet_dir: Path) -> Path:
    """Find a packet artifact even if the packet was recorded elsewhere.

    A committed packet stores the absolute paths it was written with; a checkout
    at a different path (or a packet copied into a report) still has to re-verify
    its own artifacts, so fall back to the packet's own directory.
    """
    candidate = Path(raw)
    if candidate.is_file():
        return candidate
    for fallback in (packet_dir / "questions" / candidate.name, packet_dir / candidate.name):
        if fallback.is_file():
            return fallback
    return candidate


def recheck_packet(path: Path, *, strict_manifest: bool = True) -> dict:
    """Re-verify every bundle in a packet directory NOW. Nothing is cached.

    A bundle is admissible for the ceremony only if it still passes every
    blocking check *and* still hashes to the value recorded at preflight: if the
    artifact drifted after preflight, it is not the artifact that was verified.
    """
    packet_file = Path(path) / "packet.json"
    if not packet_file.is_file():
        raise FileNotFoundError(f"no packet.json under {path}")
    packet = json.loads(packet_file.read_text(encoding="utf-8"))
    # Re-verify against the manifest the packet was built from (its own frozen
    # copy), not against whatever the canonical file says today.
    manifest = None
    manifest_note = None
    frozen = Path(path) / "manifest.json"
    try:
        if frozen.is_file():
            manifest = load_manifest(frozen, strict=False)
        elif QUESTIONS_PATH.is_file():
            manifest = load_manifest(QUESTIONS_PATH, strict=strict_manifest)
            manifest_note = "packet has no frozen manifest copy; the canonical file was used"
        else:
            manifest_note = "no pre-registration manifest available"
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        manifest_note = f"pre-registration manifest unusable: {exc}"
    if manifest and packet.get("manifest_sha256") and manifest["_sha256"] != packet["manifest_sha256"]:
        manifest_note = (
            f"the packet's manifest copy hashes to {manifest['_sha256']} but the packet recorded "
            f"{packet['manifest_sha256']}"
        )
        manifest = None
    questions: list[dict] = []
    for entry in packet.get("questions") or []:
        qid = entry.get("qid")
        qfile_path = _resolve_artifact(
            entry.get("question_path") or f"questions/{qid}.question.json", Path(path))
        bundle_path = _resolve_artifact(
            entry.get("bundle_path") or f"questions/{qid}.bundle.json", Path(path))
        record: dict[str, Any] = {
            "qid": qid,
            "language": entry.get("language"),
            "question": entry.get("question"),
            "bundle_path": str(bundle_path),
            "question_path": str(qfile_path),
            "present": bundle_path.is_file(),
        }
        if not record["present"]:
            record.update({"admissible": False, "error": "bundle file is missing"})
            questions.append(record)
            continue
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        question_spec = None
        if manifest:
            question_spec = next((q for q in manifest["questions"] if q.get("qid") == qid), None)
        verdict = verify_bundle(bundle, question=question_spec) if question_spec else verify_bundle(bundle)
        verdict["verified_at"] = _now()
        recorded = None
        if qfile_path.is_file():
            qfile = json.loads(qfile_path.read_text(encoding="utf-8"))
            recorded = (qfile.get("bundle") or {}).get("content_sha256")
            record["deep_link"] = qfile.get("deep_link")
            record["finalize_command"] = qfile.get("finalize_command")
            record["guards"] = qfile.get("guards")
        current = content_sha256(bundle)
        drift = bool(recorded) and recorded != current
        if drift:
            verdict["findings"].append({
                "code": "bundle_drifted_since_preflight", "severity": "blocking",
                "detail": f"content_sha256 {current} != {recorded} recorded at preflight; "
                          "this artifact is not the one that was verified",
            })
            verdict["blocking_count"] += 1
            verdict["admissible"] = False
        record.update({
            "admissible": verdict["admissible"],
            "verdict": verdict,
            "content_sha256": current,
            "recorded_content_sha256": recorded,
            "drifted": drift,
        })
        questions.append(record)

    blocked = [q["qid"] for q in questions if not q.get("admissible")]
    return {
        "schema": "product-gate-packet-recheck/1",
        "packet_id": packet.get("packet_id"),
        "packet_dir": str(path),
        "checked_at": _now(),
        "mode": packet.get("mode"),
        "manifest_sha256": (manifest or {}).get("_sha256"),
        "manifest_note": manifest_note,
        "rechecked": True,
        "n_questions": len(questions),
        "admissible_questions": [q["qid"] for q in questions if q.get("admissible")],
        "blocked_questions": blocked,
        "ready_for_owner_session": bool(
            questions and not blocked and packet.get("mode") == "live"
            and all((q.get("guards") or {}).get("ok") for q in questions)
        ),
        "questions": questions,
        "claim_ceiling": packet.get("claim_ceiling"),
    }


def _disclosure_lines(verdict: dict) -> list[str]:
    """Render every non-blocking finding, labelled by what it is.

    An ``info`` row is a POSITIVE disclosure (e.g. "N of the counter rows came
    through the independent adversarial route").  Printing it with the same
    bullet as a warning taught the owner to read the card as a list of defects;
    printing it unlabelled, next to a stale negative, is how the reverse error
    happens.  Both severities are shown; the label says which is which.
    """
    out = []
    for f in (verdict.get("findings") or []):
        if f.get("severity") == "blocking":
            continue
        tag = "note" if f.get("severity") == "info" else "warning"
        out.append(f"    - [{tag}] {f['code']}: {f['detail']}")
    return out


def seed_runs(recheck: dict) -> dict[str, str]:
    """Register each admissible packet bundle in the served app's run registry.

    The ceremony must show the jurist the artifact the admissibility check
    actually passed, not a fresh retrieval that merely looks similar: a re-run
    question can return a different decision set, and then the session would be
    finalized against a bundle the jurist never saw. So ``card --serve`` seeds
    the verified bundles and the deep links point at those runs.
    """
    import query_app

    seeded: dict[str, str] = {}
    for q in recheck.get("questions") or []:
        if not q.get("admissible"):
            continue
        bundle = json.loads(Path(q["bundle_path"]).read_text(encoding="utf-8"))
        seeded[q["qid"]] = query_app._remember(
            str(bundle.get("query") or ""), len(bundle.get("decisions") or []), bundle, mode="gate_packet"
        )
    return seeded


def owner_card(recheck: dict, *, base_url: str, top_n: int, run_ids: dict[str, str] | None = None) -> str:
    """The one page the owner needs: three questions, their deep links, their disclosures."""
    mode = recheck.get("mode")
    run_ids = run_ids or {}
    lines = [
        "",
        "=" * 78,
        " LexMachina comparative human gate — multi-question packet",
        "=" * 78,
        f"  packet {recheck.get('packet_id')} · mode {mode} · re-verified {recheck.get('checked_at')}",
    ]
    if mode != "live":
        lines.append(
            "  !! FIXTURE MODE — this packet is a machinery rehearsal, NOT gate material."
        )
    lines += [
        "",
        "  For EACH question: open its link, work the MAP, switch to LIST and work it",
        "  again, answer the four questions in the sidebar, press",
        '  "Exporter la session", then run that question\'s finalize command.',
        "  A \"no\" is a valid result. Nothing here is recorded until you finalize it.",
    ]
    for i, q in enumerate(recheck.get("questions") or [], start=1):
        verdict = q.get("verdict") or {}
        measured = verdict.get("measured") or {}
        ok = q.get("admissible")
        lines += [
            "",
            f"  [{i}/{len(recheck.get('questions') or [])}] {q.get('qid')} ({str(q.get('language')).upper()}) — "
            + ("READY" if ok else "BLOCKED, do not use"),
            f"      {q.get('question')}",
        ]
        if ok:
            if run_ids.get(q.get("qid")):
                link = f"{base_url}/?" + urllib.parse.urlencode({"run_id": run_ids[q["qid"]]})
                lines.append(f"      open:      {link}   (this packet's verified bundle, served)")
            elif q.get("deep_link"):
                lines.append(f"      open:      {q['deep_link']}   (re-runs the question on the served app)")
        lines += [
            f"      bundle:    {q.get('bundle_path')}",
            f"      map:       {measured.get('n_decisions')} decisions · {measured.get('n_clusters')} clusters · "
            f"{measured.get('n_counter_authorities')} ringed counter rows of "
            f"{measured.get('n_rows_with_counter_status')} with a counter status · "
            f"{measured.get('n_relations')} relations · content {str(measured.get('content_sha256'))[:12]}",
            f"      answer:    {measured.get('answer_status')} ({measured.get('answer_method')}), "
            f"{measured.get('answer_cited')} cited",
        ]
        under = measured.get("query_concepts_under_covered") or []
        if under:
            # The jurist judges the answer against the map, so the boundary of
            # what the corpus supports is part of the result, not a footnote.
            lines.append(
                "      coverage:  the retrieved corpus supports NO decision for these concepts of "
                f"the question: {', '.join(under)}. The answer cites only the concepts it can "
                "support; judge that boundary, do not read it as the corpus having nothing to say."
            )
        if measured.get("answer_gap_contract_fired"):
            lines.append(
                "      note:      the generative model cited nothing here, so the cited extract is "
                "the product's verbatim fallback (concept_coverage_extractive_v1, status degraded); "
                "the model's own assessment is kept verbatim at the top of the answer."
            )
        disclosures = _disclosure_lines(verdict)
        if disclosures:
            lines.append("      disclose before judging the map:")
            lines += disclosures
        if not ok:
            for f in (verdict.get("findings") or []):
                if f.get("severity") == "blocking":
                    lines.append(f"      BLOCKING {f['code']}: {f['detail']}")
        if q.get("finalize_command"):
            lines.append(f"      finalize:  {q['finalize_command']}")
        lines.append("      answer these four for THIS question (in the page's sidebar card):")
        for qid, text in hgf.GATE_QUESTIONS.items():
            lines.append(f"        {qid}: {text}")
    lines += [
        "",
        "  human_gate_ready is set by the director from your finalized records, never",
        "  by any tool here. Exit 7 = provenance missing, exit 8 = record refused as",
        "  inadmissible; both mean the record was NOT written.",
        "=" * 78,
        "",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=("preflight", "card", "verify"))
    ap.add_argument("--packet", default=None, help="packet directory (card/verify)")
    ap.add_argument("--questions", default=None, help="alternate pre-registration manifest")
    ap.add_argument("--run-id", default="local", help="attested core-lane run id")
    ap.add_argument("--operator", default="autonomous-packet", help="attested operator")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=0, help="0 = free port")
    ap.add_argument("--fixture", action="store_true", help="deterministic offline corpus")
    ap.add_argument("--live", action="store_true", help="real OpenCaseLaw (default)")
    ap.add_argument("--top-n", "--n", dest="top_n", type=int, default=150)
    ap.add_argument("--min-decisions", type=int, default=None)
    ap.add_argument("--max-decisions", type=int, default=None)
    ap.add_argument("--out-root", default=None)
    ap.add_argument("--wait-s", type=float, default=900.0, help="per-stage wait budget")
    ap.add_argument("--stage-timeout-s", type=float, default=600.0)
    ap.add_argument("--keep-going", action="store_true", help="continue after a blocked question")
    ap.add_argument("--serve", action="store_true", help="serve the product while the owner works (card)")
    ap.add_argument("--no-manifest-check", dest="strict_manifest", action="store_false",
                    help="skip the pre-registration digest check (diagnostics only)")
    ap.add_argument("--quiet", action="store_true")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "preflight":
        code, summary = preflight(args)
        if not args.quiet:
            print(json.dumps(summary, indent=2, ensure_ascii=False))
            if summary.get("ok"):
                print(f"PACKET OK: {len(summary['admissible_questions'])}/{summary['n_questions']} "
                      f"questions admissible ({summary['mode']})")
                print(f"next: python product/gate_packet.py card --packet {summary['packet_dir']} --serve")
            else:
                print(f"PACKET NOT READY: blocked={summary.get('blocked')}", file=sys.stderr)
        return code

    path = Path(args.packet) if args.packet else DEFAULT_OUT_ROOT
    try:
        recheck = recheck_packet(path, strict_manifest=args.strict_manifest)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 9
    if args.command == "verify":
        print(json.dumps(recheck, indent=2, ensure_ascii=False))
        return 0 if not recheck["blocked_questions"] else 5

    srv = None
    run_ids: dict[str, str] = {}
    port = args.port or 8791
    if args.serve:
        from query_app import make_server

        port = args.port or free_port()
        fixture_mode = (recheck.get("mode") == "fixture")
        srv = make_server(args.host, port, fixture_mode=fixture_mode, verbose=not args.quiet)
        if not recheck["blocked_questions"]:
            run_ids = seed_runs(recheck)
    base_url = f"http://{args.host}:{port}"
    print(owner_card(recheck, base_url=base_url, top_n=args.top_n, run_ids=run_ids))
    if recheck["blocked_questions"]:
        print("::error::blocked questions in this packet: "
              + ", ".join(recheck["blocked_questions"]), file=sys.stderr)
    if srv is not None:
        if run_ids:
            print(f"  serving this packet's verified bundles on {base_url}/ "
                  f"({len(run_ids)} run(s) pre-loaded; Ctrl-C to stop)")
        else:
            print(f"  serving the product on {base_url}/ (Ctrl-C to stop)")
        try:
            srv.serve_forever()
        except KeyboardInterrupt:  # pragma: no cover - interactive
            print("\nstopped")
        finally:
            srv.shutdown()
            srv.server_close()
    return 0 if not recheck["blocked_questions"] else 5


if __name__ == "__main__":
    raise SystemExit(main())