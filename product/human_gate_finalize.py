"""Finalize an exported human-gate session into accepted lane evidence.

Why this exists
---------------
Direction v51 names this as one of the two remaining owner-independent deltas:
*"finalize exported session draft into results/product/ via the accepted CLI"*.

The accepted ``frontier-human-gate-harness`` switch (adopted verbatim as
``product/static/lex_gate_switch.js``) lets the owner answer the four Master
Prompt gate questions in the browser and press **Exporter la session**. It
exports a ``status: "draft"`` record. Three things are still open when that file
lands on disk, and all three are mechanical, not judgement:

1. **Provenance.** The draft deliberately ships ``bundle_sha256: null``,
   ``query_sha256: null``, ``bundle_hash_status: "not_verified"`` — the harness
   is a browser asset and cannot hash the bundle itself. This CLI closes that
   hole against the exact bundle the session was run on.
2. **Integrity.** Nothing checks that the decisions the owner says they opened
   exist in the bundle, or that the "counter authorities opened" really are
   decisions carrying a counter status. That is forgeable by hand; it is not
   forgeable against a bundle digest.
3. **Aggregation.** A session is evidence only once it is finalized, addressed,
   and derivable from a run.

What this tool will never do
----------------------------
* It never writes ``human_gate_ready: true`` and never invents an answer. The
  four gate answers are the jurist's words; a missing answer yields
  ``status: "incomplete"`` and exit code 3.
* It never judges the answers. A session in which the jurist answered "no" four
  times is a valid, valuable, *negative* result — that is the Master Prompt's
  "if not, stop the standalone product" case and it must survive the pipeline
  just like a positive one.

Usage
-----
    # 1. owner exports the draft from the browser, answers q1..q4
    python product/human_gate_finalize.py --draft ~/Downloads/lex_session_draft.json \
        --bundle results/product/clickable_slice/bundle_live_enriched_*.json \
        --answers answers.json --out results/product/human_gate_sessions

    answers.json (owner verbatim, either shape accepted):
        {"q1": "yes - the exception branch in FR 4A was invisible in the list", ...}
        {"q1": {"rating": "yes", "note": "..."}, ...}

Exit codes: 0 finalized, 3 incomplete (answers missing), 4 invalid draft,
5 bundle mismatch, 6 I/O error.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Iterable, Sequence

PRODUCT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PRODUCT_ROOT.parent

#: The four comparative questions from the Master Prompt's human product gate,
#: verbatim in intent, pinned here so a session record is self-describing.
GATE_QUESTIONS: dict[str, str] = {
    "q1": "Did the map expose a relevant branch, exception or decision that was less visible in the list/answer?",
    "q2": "Did the map make the jurisprudential structure easier to understand?",
    "q3": "Did the map increase confidence that contrary authority had not been hidden?",
    "q4": "Was the combined answer + map preferable to the conventional interface?",
}

ALLOWED_RATINGS = ("yes", "partly", "no", "mixed", "not_applicable")
DEFAULT_OUT_DIR = REPO_ROOT / "results" / "product" / "human_gate_sessions"


class FinalizeError(RuntimeError):
    def __init__(self, message: str, exit_code: int) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def canonical_sha256(payload: Any) -> str:
    """Digest of the canonical JSON serialisation (stable key order, no spacing)."""
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_time(value: Any) -> dt.datetime | None:
    if not isinstance(value, str) or not value:
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        stamp = dt.datetime.fromisoformat(text)
    except ValueError:
        return None
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=dt.timezone.utc)
    return stamp


def validate_draft(draft: Any) -> list[str]:
    """Structural validation of an exported ``lex_human_gate_session``."""
    problems: list[str] = []
    if not isinstance(draft, dict):
        return ["draft is not a JSON object"]
    if draft.get("record_type") != "lex_human_gate_session":
        problems.append(f"record_type={draft.get('record_type')!r}, expected 'lex_human_gate_session'")
    if draft.get("team_id") != "frontier-human-gate-harness":
        problems.append(f"team_id={draft.get('team_id')!r}, expected 'frontier-human-gate-harness'")
    for key in ("query", "started_at", "ended_at", "actions", "decisions_opened", "counter_authorities_opened"):
        if key not in draft:
            problems.append(f"missing required key {key!r}")
    if not isinstance(draft.get("actions"), list):
        problems.append("actions must be a list")
    elif not draft["actions"]:
        problems.append("actions is empty: a session with no recorded interaction is not evidence")
    for key in ("decisions_opened", "counter_authorities_opened"):
        if key in draft and not isinstance(draft[key], list):
            problems.append(f"{key} must be a list")
    for key in ("started_at", "ended_at"):
        if key in draft and _parse_time(draft.get(key)) is None:
            problems.append(f"{key} must be an ISO-8601 timestamp, got {draft.get(key)!r}")
    started, ended = _parse_time(draft.get("started_at")), _parse_time(draft.get("ended_at"))
    if started and ended and ended < started:
        problems.append("ended_at precedes started_at")
    return problems


def normalize_answers(raw: Any, draft_answers: Any = None) -> tuple[dict[str, dict], list[str]]:
    """Normalise owner answers to ``{q_id: {rating, note}}`` without inventing any."""
    merged: dict[str, Any] = {}
    if isinstance(draft_answers, dict):
        merged.update(draft_answers)
    if isinstance(raw, dict):
        merged.update(raw)
    normalized: dict[str, dict] = {}
    for qid in GATE_QUESTIONS:
        value = merged.get(qid)
        if value is None:
            continue
        if isinstance(value, dict):
            rating = str(value.get("rating") or value.get("answer") or "").strip().lower()
            note = str(value.get("note") or value.get("text") or "").strip()
        else:
            rating, note = "", str(value).strip()
            if note.lower() in ALLOWED_RATINGS:
                rating, note = note.lower(), ""
        if rating and rating not in ALLOWED_RATINGS:
            rating = ""
        if not rating and not note:
            continue
        normalized[qid] = {"rating": rating, "note": note}
    return normalized, [q for q in GATE_QUESTIONS if q not in normalized]


def bundle_evidence(draft: dict, bundle: dict | None) -> dict:
    """Cross-check the session against the bundle it was run on."""
    ref = draft.get("bundle_ref") or {}
    evidence: dict[str, Any] = {
        "bundle_supplied": bundle is not None,
        "bundle_ref_query": ref.get("query"),
        "bundle_ref_n_decisions": ref.get("n_decisions"),
    }
    if bundle is None:
        evidence["bundle_hash_status"] = "not_verified"
        evidence["note"] = "no bundle supplied: the session stays draft evidence, not accepted evidence"
        return evidence

    evidence["bundle_sha256"] = canonical_sha256(bundle)
    evidence["query_sha256"] = canonical_sha256(bundle.get("query"))
    decisions = bundle.get("decisions") or []
    by_id = {str(d.get("decision_id")): d for d in decisions if isinstance(d, dict) and d.get("decision_id")}
    counter_ids = {
        str(d.get("decision_id"))
        for d in decisions
        if isinstance(d, dict) and (d.get("counter_status") or "none") not in ("none", "", None)
    }
    opened = [str(x) for x in (draft.get("decisions_opened") or [])]
    counters = [str(x) for x in (draft.get("counter_authorities_opened") or [])]
    evidence.update(
        {
            "bundle_decision_count": len(decisions),
            "bundle_counter_count": len(counter_ids),
            "query_matches_bundle": ref.get("query") == bundle.get("query"),
            "opened_in_bundle": sum(1 for d in opened if d in by_id),
            "opened_not_in_bundle": sorted({d for d in opened if d not in by_id}),
            "counters_in_bundle": sum(1 for c in counters if c in counter_ids),
            "counters_not_counter_status": sorted({c for c in counters if c not in counter_ids}),
        }
    )
    integrity_problems: list[str] = []
    if ref.get("query") != bundle.get("query"):
        integrity_problems.append("draft query does not match the supplied bundle query")
    if evidence["opened_not_in_bundle"]:
        integrity_problems.append("decisions_opened references ids absent from the bundle")
    if evidence["counters_not_counter_status"]:
        integrity_problems.append("counter_authorities_opened references ids without a counter status")
    evidence["integrity_problems"] = integrity_problems
    evidence["bundle_hash_status"] = "verified" if not integrity_problems else "mismatch"
    return evidence


def session_metrics(draft: dict) -> dict:
    actions = draft.get("actions") or []
    events: dict[str, int] = {}
    for action in actions:
        if isinstance(action, dict):
            name = str(action.get("event") or "unknown")
            events[name] = events.get(name, 0) + 1
    started, ended = _parse_time(draft.get("started_at")), _parse_time(draft.get("ended_at"))
    wall = (ended - started).total_seconds() if started and ended else None
    list_actions = sum(1 for a in actions if isinstance(a, dict) and a.get("view_mode") == "list")
    return {
        "n_actions": len(actions),
        "events": events,
        "n_view_switches": sum(events.get(name, 0) for name in ("switch", "switch_view", "view_switch")),
        "list_mode_actions": list_actions,
        "view_mode_initial": draft.get("view_mode_initial"),
        "view_mode_final": draft.get("view_mode_final"),
        "used_conventional_baseline": list_actions > 0,
        "n_decisions_opened": len(draft.get("decisions_opened") or []),
        "n_counter_authorities_opened": len(draft.get("counter_authorities_opened") or []),
        "wall_clock_seconds": round(wall, 3) if wall is not None else None,
    }


def finalize(
    draft: dict,
    answers_raw: Any = None,
    bundle: dict | None = None,
    *,
    run_id: str | None = None,
    finalized_by: str | None = None,
    session_id: str | None = None,
    now: str | None = None,
) -> dict:
    """Return the finalized session record. Raises :class:`FinalizeError`."""
    problems = validate_draft(draft)
    if problems:
        raise FinalizeError("invalid draft: " + "; ".join(problems), exit_code=4)

    answers, missing = normalize_answers(answers_raw, draft.get("answers"))
    metrics = session_metrics(draft)
    evidence = bundle_evidence(draft, bundle)
    if evidence.get("bundle_hash_status") == "mismatch":
        raise FinalizeError(
            "bundle/session mismatch: " + "; ".join(evidence["integrity_problems"]),
            exit_code=5,
        )

    stamp = now or _utc_now()
    resolved_session_id = session_id or draft.get("session_id") or f"session-{stamp.replace(':', '').replace('-', '')}"
    status = "finalized" if not missing else "incomplete"
    record = dict(draft)
    record.update(
        {
            "schema_version": draft.get("schema_version", "1.0"),
            "status": status,
            "session_id": resolved_session_id,
            "session_id_origin": draft.get("session_id_origin") or ("operator" if session_id else "auto"),
            "gate_questions": GATE_QUESTIONS,
            "answers": answers,
            "missing_answers": missing,
            "bundle_sha256": evidence.get("bundle_sha256"),
            "query_sha256": evidence.get("query_sha256"),
            "bundle_hash_status": evidence.get("bundle_hash_status"),
            "bundle_evidence": evidence,
            "session_metrics": metrics,
            "latency": {
                **dict(draft.get("latency") or {}),
                "session_wall_clock_seconds": metrics["wall_clock_seconds"],
            },
            "finalized_at": stamp,
            "finalized_by": finalized_by,
            "run_id": run_id,
            "claim_ceiling": (
                "human gate EVIDENCE only: this record documents one owner/jurist session. "
                "human_gate_ready is set by the director from these records, never by this tool."
            ),
        }
    )
    if missing and status == "incomplete":
        raise IncompleteSession(record, missing, exit_code=3)
    return record


class IncompleteSession(FinalizeError):
    """A structurally valid session whose gate answers are not all present."""

    def __init__(self, record: dict, missing: Sequence[str], exit_code: int = 3) -> None:
        super().__init__(
            "missing answers for " + ", ".join(missing) + "; session recorded as incomplete evidence",
            exit_code,
        )
        self.record = record
        self.missing = list(missing)


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FinalizeError(f"file not found: {path}", exit_code=6) from exc
    except json.JSONDecodeError as exc:
        raise FinalizeError(f"{path} is not valid JSON: {exc}", exit_code=4) from exc


def load_answers(source: Iterable[str] | str | None) -> Any:
    if not source:
        return None
    items = [source] if isinstance(source, str) else list(source)
    merged: dict[str, Any] = {}
    for item in items:
        payload = load_json(Path(item))
        if isinstance(payload, dict) and set(payload) & set(GATE_QUESTIONS):
            merged.update(payload)
        else:  # a list of {question_id, answer} rows
            for row in payload if isinstance(payload, list) else []:
                if isinstance(row, dict) and row.get("question_id") in GATE_QUESTIONS:
                    merged[row["question_id"]] = row.get("answer", row.get("rating"))
    return merged or None


def write_record(record: dict, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_id = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in str(record["session_id"]))
    target = out_dir / f"session_{safe_id}.json"
    target.write_text(json.dumps(record, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return target


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Finalize an exported human-gate session draft.")
    parser.add_argument("--draft", required=True, help="draft JSON exported by the session button")
    parser.add_argument("--bundle", default=None, help="the query_result_bundle the session was run on")
    parser.add_argument(
        "--answers",
        action="append",
        default=None,
        help="owner answers, JSON file (repeatable); merged left to right",
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--run-id", default=None, help="core-lane run this session belongs to")
    parser.add_argument("--finalized-by", default=None, help="who ran the finalizer (free text)")
    parser.add_argument("--session-id", default=None, help="override the session id")
    parser.add_argument("--dry-run", action="store_true", help="validate and print, write nothing")
    args = parser.parse_args(argv)

    try:
        draft = load_json(Path(args.draft))
        bundle = load_json(Path(args.bundle)) if args.bundle else None
        answers = load_answers(args.answers)
        record = finalize(
            draft,
            answers,
            bundle,
            run_id=args.run_id,
            finalized_by=args.finalized_by,
            session_id=args.session_id,
        )
    except IncompleteSession as incomplete:
        if not args.dry_run:
            path = write_record(incomplete.record, args.out)
            print(f"incomplete session recorded: {path}")
        print(f"::error::{incomplete}", file=sys.stderr)
        print(
            "answers still required: "
            + ", ".join(f"{q} — {GATE_QUESTIONS[q]}" for q in incomplete.missing),
            file=sys.stderr,
        )
        return incomplete.exit_code
    except FinalizeError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return exc.exit_code

    if args.dry_run:
        print(json.dumps(record, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    path = write_record(record, args.out)
    print(f"finalized: {path}")
    print(
        f"  session={record['session_id']} status={record['status']} "
        f"bundle_hash_status={record['bundle_hash_status']} "
        f"opened={record['session_metrics']['n_decisions_opened']} "
        f"counters_opened={record['session_metrics']['n_counter_authorities_opened']} "
        f"used_baseline={record['session_metrics']['used_conventional_baseline']}"
    )
    print("  human_gate_ready is NOT set by this tool; it records one session's evidence.")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI
    sys.exit(main())