"""Session capture: the claim-bearing record of an owner gate sitting.

Acceptance test (4): a capture routine writing a machine-readable session record
(``results/frontier/frontier-human-gate-harness/session_<id>.json``) containing
bundle/query hash, view mode per action, decisions opened, counter-authorities
opened, timestamped answers to the four questions and wall-clock latency — no
personal data, no fabricated entries, no silent defaults for missing answers.

Acceptance test (6): the capture *rejects* a missing answer instead of inventing
one — :func:`finalize` raises :class:`MissingAnswerError` unless the caller
explicitly opts into an incomplete record, which is then labelled
``status="incomplete"`` with the missing ids spelled out.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .bundle_io import bundle_sha256, canonical_json, sha256_text
from .owner_card import QUESTION_IDS

SCHEMA_VERSION = "1.0"
RECORD_TYPE = "lex_human_gate_session"
TEAM_ID = "frontier-human-gate-harness"
CHARTER_VERSION = 1

RECORD_KEYS = [
    "schema_version", "record_type", "team_id", "charter_version",
    "session_id", "session_id_origin", "status", "source",
    "query", "bundle_ref", "bundle_sha256", "bundle_hash_status",
    "started_at", "ended_at", "wall_clock_seconds",
    "view_mode_initial", "view_mode_final",
    "actions", "decisions_opened", "counter_authorities_opened",
    "answers", "missing_answers", "latency",
]
STATUS_VALUES = ["empty", "draft", "incomplete", "complete"]
SOURCE_TOKENS = {"switch", "card", "demo", "cli"}
SESSION_ORIGIN_VALUES = {"draft", "card_field", "cli_flag", "derived_from_bundle_sha256", None}
HASH_STATUS_VALUES = ["computed", "not_verified"]
ACTION_EVENTS = {"switch", "open_decision", "open_counter", "render", "session_start"}
VIEW_MODES = {"map", "list"}
ANSWER_KEYS = {"scale", "text", "answered_at"}
BUNDLE_REF_KEYS = {"query", "n_decisions"}
LATENCY_KEYS = {"baseline_render_ms", "session_wall_clock_seconds"}

#: Keys that would make the record personal data. The schema never contains them.
PERSONAL_KEYS = {
    "name", "firstname", "lastname", "full_name", "email", "e-mail", "mail",
    "user", "username", "participant", "author", "owner_name", "ip", "ip_address",
    "address", "phone", "telephone", "device", "fingerprint", "session_owner",
}

ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?Z$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")


class CaptureError(ValueError):
    """Capture record is structurally invalid."""


class MissingAnswerError(CaptureError):
    """At least one of the four gate questions has no answer — never invent one."""

    def __init__(self, missing: list[str], answered: list[str]):
        self.missing = sorted(missing)
        self.answered = sorted(answered)
        super().__init__(
            "capture rejected: missing answer(s) for "
            f"{', '.join(self.missing) or '<none>'} "
            f"(answered: {', '.join(self.answered) or '<none>'}). "
            "No default is written; answer the card and export again, or pass "
            "--allow-incomplete to write an explicitly labelled incomplete record."
        )


def now_iso() -> str:
    """UTC second-precision timestamp; LEX_HARNESS_NOW makes runs reproducible."""
    fixed = os.environ.get("LEX_HARNESS_NOW")
    if fixed:
        return fixed
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(value: Any, field: str, errors: list[str]) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str) or not ISO_RE.match(value):
        errors.append(f"{field} must be an ISO-8601 Z string or null, got {value!r}")
        return None
    try:
        normalised = value.split(".", 1)[0]
        return datetime.strptime(normalised, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        errors.append(f"{field} is not a valid timestamp: {value!r}")
        return None


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def new_record(*, session_id: str | None, session_id_origin: str | None, status: str,
               source: str, query: str | None, bundle_ref: dict,
               bundle_sha256_value: str | None, bundle_hash_status: str,
               started_at: str | None, ended_at: str | None,
               view_mode_initial: str | None, view_mode_final: str | None,
               actions: list[dict], decisions_opened: list[str],
               counter_authorities_opened: list[str], answers: dict,
               missing_answers: list[str], latency: dict,
               wall_clock_seconds: float | None) -> dict:
    record = {
        "schema_version": SCHEMA_VERSION,
        "record_type": RECORD_TYPE,
        "team_id": TEAM_ID,
        "charter_version": CHARTER_VERSION,
        "session_id": session_id,
        "session_id_origin": session_id_origin,
        "status": status,
        "source": source,
        "query": query,
        "bundle_ref": dict(bundle_ref),
        "bundle_sha256": bundle_sha256_value,
        "bundle_hash_status": bundle_hash_status,
        "started_at": started_at,
        "ended_at": ended_at,
        "wall_clock_seconds": wall_clock_seconds,
        "view_mode_initial": view_mode_initial,
        "view_mode_final": view_mode_final,
        "actions": list(actions),
        "decisions_opened": list(decisions_opened),
        "counter_authorities_opened": list(counter_authorities_opened),
        "answers": dict(answers),
        "missing_answers": sorted(missing_answers),
        "latency": dict(latency),
    }
    return record


def missing_for(answers: dict) -> list[str]:
    return [qid for qid in QUESTION_IDS if qid not in answers]


def empty_capture(bundle: dict | None = None, *, session_id: str | None = None,
                  now: str | None = None) -> dict:
    """Empty capture written by the one-command offline path (acceptance 5).

    ``session_id`` defaults to a value *derived from the bundle hash* so the file
    name and the record are byte-reproducible; the derivation is declared in
    ``session_id_origin`` and is never presented as an observed session.
    """
    stamp = now or now_iso()
    bundle_ref = {"query": None, "n_decisions": None}
    sha = None
    if bundle is not None:
        bundle_ref = {"query": bundle.get("query"), "n_decisions": len(bundle.get("decisions") or [])}
        sha = bundle_sha256(bundle)
        if session_id is None:
            session_id = f"empty_{sha[:12]}"
            origin = "derived_from_bundle_sha256"
        else:
            origin = "cli_flag"
    else:
        origin = "cli_flag" if session_id else None
    return new_record(
        session_id=session_id, session_id_origin=origin, status="empty", source="cli",
        query=(bundle or {}).get("query"), bundle_ref=bundle_ref,
        bundle_sha256_value=sha, bundle_hash_status="computed" if sha else "not_verified",
        started_at=None, ended_at=stamp, wall_clock_seconds=None,
        view_mode_initial=None, view_mode_final=None,
        actions=[], decisions_opened=[], counter_authorities_opened=[],
        answers={}, missing_answers=list(QUESTION_IDS),
        latency={"baseline_render_ms": None, "session_wall_clock_seconds": None},
    )


def validate_record(record: dict, *, expected_status: Iterable[str] | None = None) -> list[str]:
    """Structural validation. Returns [] when the record is valid."""
    errors: list[str] = []
    if not isinstance(record, dict):
        return ["record must be a JSON object"]
    keys = list(record.keys())
    if set(keys) != set(RECORD_KEYS):
        extra = sorted(set(keys) - set(RECORD_KEYS))
        absent = sorted(set(RECORD_KEYS) - set(keys))
        if extra:
            errors.append(f"unknown key(s): {', '.join(extra)}")
        if absent:
            errors.append(f"missing key(s): {', '.join(absent)}")
        if extra or absent:
            return errors

    if record["schema_version"] != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION!r}")
    if record["record_type"] != RECORD_TYPE:
        errors.append(f"record_type must be {RECORD_TYPE!r}")
    if record["team_id"] != TEAM_ID:
        errors.append(f"team_id must be {TEAM_ID!r}")
    if record["charter_version"] != CHARTER_VERSION:
        errors.append(f"charter_version must be {CHARTER_VERSION}")
    if record["status"] not in STATUS_VALUES:
        errors.append(f"status must be one of {STATUS_VALUES}")
    if expected_status is not None and record["status"] not in set(expected_status):
        errors.append(f"status must be one of {sorted(set(expected_status))}")
    if not isinstance(record["session_id"], str) and record["session_id"] is not None:
        errors.append("session_id must be a string or null")
    if record["session_id_origin"] not in SESSION_ORIGIN_VALUES:
        errors.append(f"session_id_origin must be one of {sorted(str(v) for v in SESSION_ORIGIN_VALUES)}")
    if isinstance(record["session_id"], str) and not record["session_id"].strip():
        errors.append("session_id must be non-empty when present")
    if isinstance(record["session_id"], str) and record["session_id_origin"] is None:
        errors.append("session_id present without session_id_origin (silent default forbidden)")

    tokens = str(record["source"]).split("+")
    if not tokens or any(t not in SOURCE_TOKENS for t in tokens):
        errors.append(f"source must be tokens from {sorted(SOURCE_TOKENS)} joined by '+'")

    if record["query"] is not None and not isinstance(record["query"], str):
        errors.append("query must be a string or null")

    ref = record["bundle_ref"]
    if not isinstance(ref, dict) or set(ref.keys()) != BUNDLE_REF_KEYS:
        errors.append(f"bundle_ref must have exactly the keys {sorted(BUNDLE_REF_KEYS)}")
    else:
        if ref["query"] is not None and not isinstance(ref["query"], str):
            errors.append("bundle_ref.query must be a string or null")
        if ref["n_decisions"] is not None and not _is_int(ref["n_decisions"]):
            errors.append("bundle_ref.n_decisions must be an integer or null")

    sha = record["bundle_sha256"]
    if sha is not None and (not isinstance(sha, str) or not SHA_RE.match(sha)):
        errors.append("bundle_sha256 must be a sha256 hex string or null")
    if record["bundle_hash_status"] not in HASH_STATUS_VALUES:
        errors.append(f"bundle_hash_status must be one of {HASH_STATUS_VALUES}")
    if record["bundle_hash_status"] == "computed" and sha is None:
        errors.append("bundle_hash_status=computed requires bundle_sha256")
    if record["bundle_hash_status"] == "not_verified" and sha is not None:
        errors.append("bundle_sha256 present while bundle_hash_status=not_verified")

    started = _parse_iso(record["started_at"], "started_at", errors)
    ended = _parse_iso(record["ended_at"], "ended_at", errors)
    if record["view_mode_initial"] is not None and record["view_mode_initial"] not in VIEW_MODES:
        errors.append(f"view_mode_initial must be one of {sorted(VIEW_MODES)} or null")
    if record["view_mode_final"] is not None and record["view_mode_final"] not in VIEW_MODES:
        errors.append(f"view_mode_final must be one of {sorted(VIEW_MODES)} or null")

    wall = record["wall_clock_seconds"]
    if wall is not None and (not isinstance(wall, (int, float)) or isinstance(wall, bool)):
        errors.append("wall_clock_seconds must be a number or null")
    if started and ended and isinstance(wall, (int, float)):
        expected = round((ended - started).total_seconds(), 3)
        if abs(expected - float(wall)) > 1.0:
            errors.append(f"wall_clock_seconds {wall} inconsistent with timestamps ({expected})")

    if not isinstance(record["actions"], list):
        errors.append("actions must be a list")
    else:
        for i, action in enumerate(record["actions"]):
            if not isinstance(action, dict) or set(action.keys()) != {"at", "view_mode", "event", "ref"}:
                errors.append(f"actions[{i}] must have exactly keys at, view_mode, event, ref")
                continue
            _parse_iso(action["at"], f"actions[{i}].at", errors)
            if action["view_mode"] not in VIEW_MODES:
                errors.append(f"actions[{i}].view_mode must be one of {sorted(VIEW_MODES)}")
            if action["event"] not in ACTION_EVENTS:
                errors.append(f"actions[{i}].event must be one of {sorted(ACTION_EVENTS)}")
            if action["ref"] is not None and not isinstance(action["ref"], str):
                errors.append(f"actions[{i}].ref must be a string or null")

    for field in ("decisions_opened", "counter_authorities_opened"):
        value = record[field]
        if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
            errors.append(f"{field} must be a list of strings")
        elif len(value) != len(dict.fromkeys(value)):
            errors.append(f"{field} must not contain duplicates")

    answers = record["answers"]
    if not isinstance(answers, dict):
        errors.append("answers must be an object")
    else:
        for qid, answer in answers.items():
            if qid not in QUESTION_IDS:
                errors.append(f"unknown question id: {qid}")
                continue
            if not isinstance(answer, dict) or set(answer.keys()) != ANSWER_KEYS:
                errors.append(f"answers.{qid} must have exactly keys {sorted(ANSWER_KEYS)}")
                continue
            scale, text = answer["scale"], answer["text"]
            if scale is not None and (not _is_int(scale) or not SCALE_OK(scale)):
                errors.append(f"answers.{qid}.scale must be an integer 1..5 or null")
            if not isinstance(text, str):
                errors.append(f"answers.{qid}.text must be a string")
            _parse_iso(answer["answered_at"], f"answers.{qid}.answered_at", errors)
            empty_scale = scale is None
            empty_text = isinstance(text, str) and not text.strip()
            if empty_scale and empty_text:
                errors.append(f"answers.{qid} is empty (no scale and no text) — "
                              "an empty answer is treated as missing, never as answered")

    expected_missing = missing_for(answers if isinstance(answers, dict) else {})
    if record["missing_answers"] != expected_missing:
        errors.append(
            f"missing_answers must be exactly {expected_missing} for the given answers "
            f"(got {record['missing_answers']}) — silent defaults are forbidden"
        )

    latency = record["latency"]
    if not isinstance(latency, dict) or set(latency.keys()) != LATENCY_KEYS:
        errors.append(f"latency must have exactly the keys {sorted(LATENCY_KEYS)}")
    else:
        for key in LATENCY_KEYS:
            value = latency[key]
            if value is not None and (not isinstance(value, (int, float)) or isinstance(value, bool)):
                errors.append(f"latency.{key} must be a number or null")

    errors.extend(personal_data_errors(record))
    return errors


def SCALE_OK(scale: int) -> bool:
    return 1 <= scale <= 5


def personal_data_errors(record: dict) -> list[str]:
    """The record must not carry personal-data fields anywhere in its key tree."""
    found: list[str] = []

    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if isinstance(key, str) and key.lower() in PERSONAL_KEYS:
                    found.append(f"{path}.{key}" if path else key)
                walk(value, f"{path}.{key}" if path else str(key))
        elif isinstance(node, list):
            for i, value in enumerate(node):
                walk(value, f"{path}[{i}]")

    walk(record, "")
    return [f"personal-data key forbidden: {p}" for p in found]


def _unique_extend(target: list[str], values: Iterable[str]) -> None:
    for value in values:
        if value not in target:
            target.append(value)


def merge_drafts(drafts: list[dict], *, session_id: str | None = None,
                 session_id_origin: str | None = None) -> dict:
    """Merge switch/card/demo drafts into one record body. Conflicts are errors."""
    if not drafts:
        raise CaptureError("no drafts supplied")
    for i, draft in enumerate(drafts):
        errors = validate_record(draft)
        if errors:
            raise CaptureError(f"draft[{i}] invalid: " + "; ".join(errors))

    # session id: every non-null value must agree
    ids = {d.get("session_id") for d in drafts if d.get("session_id")}
    if len(ids) > 1:
        raise CaptureError(f"draft session_id conflict: {sorted(ids)} — refuse to guess")
    draft_id = ids.pop() if ids else None
    if session_id is None:
        session_id = draft_id
        origin = (next(d.get("session_id_origin") for d in drafts
                       if d.get("session_id")) if draft_id else None)
    else:
        origin = session_id_origin or "cli_flag"
        if draft_id and draft_id != session_id:
            raise CaptureError(
                f"--session-id {session_id!r} conflicts with draft session id {draft_id!r}"
            )
    if not session_id:
        raise CaptureError(
            "session_id missing: no draft carries one and no --session-id was given. "
            "Refusing to invent a session id."
        )
    if origin is None:
        raise CaptureError("session_id_origin missing for the chosen session id")

    # bundle reference: non-null values must agree
    refs = [d.get("bundle_ref") or {} for d in drafts]
    query_values = {r.get("query") for r in refs if r.get("query") is not None}
    n_values = {r.get("n_decisions") for r in refs if r.get("n_decisions") is not None}
    if len(query_values) > 1 or len(n_values) > 1:
        raise CaptureError("draft bundle_ref conflict — the drafts were not taken "
                           f"from the same query/bundle: queries={sorted(map(str, query_values))}")
    bundle_ref = {
        "query": next(iter(query_values), None),
        "n_decisions": next(iter(n_values), None),
    }

    # answers: same question answered differently in two drafts is a conflict
    answers: dict[str, dict] = {}
    for draft in drafts:
        for qid, answer in (draft.get("answers") or {}).items():
            previous = answers.get(qid)
            if previous is not None and canonical_json(previous) != canonical_json(answer):
                raise CaptureError(
                    f"conflicting answers for {qid} across drafts — refusing to pick one"
                )
            answers[qid] = answer

    actions: list[dict] = []
    for draft in drafts:
        actions.extend(draft.get("actions") or [])
    decisions_opened: list[str] = []
    counter_opened: list[str] = []
    for draft in drafts:
        _unique_extend(decisions_opened, draft.get("decisions_opened") or [])
        _unique_extend(counter_opened, draft.get("counter_authorities_opened") or [])

    sources = []
    for draft in drafts:
        for token in str(draft.get("source") or "").split("+"):
            if token and token not in sources:
                sources.append(token)

    started_values = [d.get("started_at") for d in drafts if d.get("started_at")]
    ended_values = [d.get("ended_at") for d in drafts if d.get("ended_at")]
    started = min(started_values) if started_values else None
    ended = max(ended_values) if ended_values else None
    view_initials = [d.get("view_mode_initial") for d in drafts if d.get("view_mode_initial")]
    view_finals = [d.get("view_mode_final") for d in drafts if d.get("view_mode_final")]

    wall = None
    if started and ended:
        s = _parse_iso(started, "started_at", [])
        e = _parse_iso(ended, "ended_at", [])
        if s and e:
            wall = round((e - s).total_seconds(), 3)

    queries = {d.get("query") for d in drafts if d.get("query") is not None}
    if len(queries) > 1:
        raise CaptureError(f"draft query conflict: {sorted(map(str, queries))} — refusing to guess")
    return new_record(
        session_id=session_id, session_id_origin=origin, status="draft",
        source="+".join(sources),
        query=next(iter(queries)) if queries else None,
        bundle_ref=bundle_ref, bundle_sha256_value=None, bundle_hash_status="not_verified",
        started_at=started, ended_at=ended, wall_clock_seconds=wall,
        view_mode_initial=view_initials[-1] if view_initials else None,
        view_mode_final=view_finals[-1] if view_finals else None,
        actions=actions, decisions_opened=decisions_opened,
        counter_authorities_opened=counter_opened, answers=answers,
        missing_answers=missing_for(answers),
        latency={"baseline_render_ms": None, "session_wall_clock_seconds": wall},
    )


def finalize(drafts: list[dict], *, bundle: dict | None = None,
             session_id: str | None = None, allow_incomplete: bool = False,
             now: str | None = None) -> dict:
    """Merge drafts, enforce the four answers, attach the bundle hash, stamp time.

    Raises :class:`MissingAnswerError` when any of the four questions is
    unanswered and ``allow_incomplete`` is False — the default. Nothing is ever
    filled in for a missing answer.
    """
    record = merge_drafts(drafts, session_id=session_id)
    stamp = now or now_iso()

    if bundle is not None:
        sha = bundle_sha256(bundle)
        ref = record["bundle_ref"]
        bundle_query = bundle.get("query")
        if ref["query"] is not None and ref["query"] != bundle_query:
            raise CaptureError(
                f"draft query {ref['query']!r} does not match fixture query {bundle_query!r}"
            )
        if ref["n_decisions"] is not None and ref["n_decisions"] != len(bundle.get("decisions") or []):
            raise CaptureError(
                f"draft n_decisions {ref['n_decisions']} does not match fixture "
                f"{len(bundle.get('decisions') or [])}"
            )
        record["query"] = bundle_query
        record["bundle_ref"] = {"query": bundle_query,
                                "n_decisions": len(bundle.get("decisions") or [])}
        record["bundle_sha256"] = sha
        record["bundle_hash_status"] = "computed"

    record["ended_at"] = record["ended_at"] or stamp
    record["started_at"] = record["started_at"] or stamp
    if record["wall_clock_seconds"] is None and record["started_at"] and record["ended_at"]:
        s = _parse_iso(record["started_at"], "started_at", [])
        e = _parse_iso(record["ended_at"], "ended_at", [])
        if s and e:
            record["wall_clock_seconds"] = round((e - s).total_seconds(), 3)
    record["latency"]["session_wall_clock_seconds"] = record["wall_clock_seconds"]

    missing = missing_for(record["answers"])
    record["missing_answers"] = sorted(missing)
    if missing:
        if not allow_incomplete:
            raise MissingAnswerError(missing, list(record["answers"]))
        record["status"] = "incomplete"
    else:
        record["status"] = "complete"

    errors = validate_record(record)
    if errors:
        raise CaptureError("finalised capture failed validation: " + "; ".join(errors))
    return record


def record_bytes(record: dict) -> bytes:
    return (json.dumps(record, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def session_filename(record: dict) -> str:
    session_id = record.get("session_id")
    if not isinstance(session_id, str) or not session_id.strip():
        raise CaptureError("cannot write a session record without a session_id")
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", session_id)
    return f"session_{safe}.json"


def write_session(record: dict, out_dir: str | Path) -> Path:
    errors = validate_record(record)
    if errors:
        raise CaptureError("refusing to write an invalid capture: " + "; ".join(errors))
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / session_filename(record)
    path.write_bytes(record_bytes(record))
    return path


def read_draft(path: str | Path) -> dict:
    path = Path(path)
    if not path.is_file():
        raise CaptureError(f"draft not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CaptureError(f"draft is not valid JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise CaptureError(f"draft must be a JSON object: {path}")
    return data


def capture_schema_summary() -> dict:
    """Machine-readable description of the record (also used by the test suite)."""
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": RECORD_TYPE,
        "keys": list(RECORD_KEYS),
        "question_ids": list(QUESTION_IDS),
        "status_values": list(STATUS_VALUES),
        "source_tokens": sorted(SOURCE_TOKENS),
        "action_events": sorted(ACTION_EVENTS),
        "view_modes": sorted(VIEW_MODES),
        "answer_keys": sorted(ANSWER_KEYS),
        "personal_keys_forbidden": sorted(PERSONAL_KEYS),
        "hash": {"algorithm": "sha256", "canonicalisation":
                 "json.dumps(sort_keys=True, separators=(',',':'), ensure_ascii=False)"},
    }


def bundle_hash_of(bundle: dict) -> str:
    return sha256_text(canonical_json(bundle))
