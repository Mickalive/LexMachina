"""Executable gates for the frozen retrieval/counter-authority benchmark.

Every gate returns ``{"gate", "passed", "detail", "measured"}`` so a verdict
can be recomputed from the run record alone (``evaluate(spec, record)`` is a
pure function: same record -> byte-identical verdict).  Gates an artifact
cannot support are reported ``not_measurable`` with a reason and are never
counted as passes.

All text matching uses :func:`evaluation.retrieval_gate.frozen.normalize_text`
(NFKD, diacritic-stripped, casefolded, ``<mark>`` markup stripped).  Nothing
here assigns a supporting/contrary label to a decision.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from evaluation.retrieval_gate import frozen

ROW_TEXT_FIELDS = ("title", "regeste", "snippet")
CITATION_FIELDS = ("citation_string_de", "citation_string_fr", "citation_string_it")
TEXT_HEAD_CHARS = 600


def row_cores(row: dict, min_len: int = 6) -> set[str]:
    """Alnum cores of every id-bearing field of a retrieved row.

    The docket number is only used prefixed by its court, so two unrelated
    courts sharing a docket pattern can never look like a duplicate authority.
    """
    docket = str(row.get("docket_number") or "")
    court = str(row.get("court") or "")
    docket_candidate = f"{court}_{docket}" if (court and docket) else docket
    candidates = [
        row.get("decision_id"),
        row.get("canonical_decision_id"),
        docket_candidate,
        *(row.get(f) for f in CITATION_FIELDS),
    ]
    cores = set()
    for value in candidates:
        core = frozen.alnum_core(value)
        if len(core) >= min_len and any(ch.isdigit() for ch in core):
            cores.add(core)
    return cores


def row_text(row: dict) -> str:
    """Title + regeste + snippet with search highlight markup removed, so the
    recorded ``text_head`` is readable evidence and matches token gates."""
    parts = [frozen._strip_markup(str(row.get(f) or "")) for f in ROW_TEXT_FIELDS]
    return " ".join(p for p in parts if p)


def extract_rows(body: dict | None) -> list[dict]:
    """Compact, evidence-preserving extraction of one search response."""
    rows: list[dict] = []
    for raw in (body or {}).get("results") or []:
        if not isinstance(raw, dict):
            continue
        text = row_text(raw)
        rows.append({
            "decision_id": str(raw.get("decision_id") or ""),
            "canonical_decision_id": str(raw.get("canonical_decision_id") or ""),
            "docket_number": str(raw.get("docket_number") or ""),
            "citation_string_de": str(raw.get("citation_string_de") or ""),
            "citation_string_fr": str(raw.get("citation_string_fr") or ""),
            "citation_string_it": str(raw.get("citation_string_it") or ""),
            "language": str(raw.get("language") or ""),
            "decision_date": str(raw.get("decision_date") or ""),
            "canonical_url": str(raw.get("canonical_url") or ""),
            "court": str(raw.get("court") or ""),
            "relevance_score": raw.get("relevance_score"),
            "text_head": text[:TEXT_HEAD_CHARS],
        })
    return rows


def match_authorities(authority_ids: list[str], rows: list[dict],
                      min_len: int = 6) -> dict[str, str | None]:
    """frozen authority id -> matched alnum core (or None when not retrieved)."""
    row_index: dict[str, dict] = {}
    for row in rows:
        for core in sorted(row_cores(row, min_len=min_len)):
            row_index.setdefault(core, row)
    out: dict[str, str | None] = {}
    for aid in authority_ids:
        target = frozen.alnum_core(aid)
        if len(target) < min_len:
            out[aid] = None
            continue
        out[aid] = target if target in row_index else None
    return out


def _pool(queries: list[dict], *, slug: str, channel: str | None = None,
          language: str | None = None) -> list[dict]:
    rows: list[dict] = []
    for q in queries:
        if q.get("slug") != slug:
            continue
        if channel is not None and q.get("channel") != channel:
            continue
        if language is not None and q.get("language") != language:
            continue
        rows.extend(q.get("rows") or [])
    return rows


def _failed_queries(queries: list[dict], *, slug: str) -> list[str]:
    return [q.get("query_key", "?") for q in queries
            if q.get("slug") == slug and q.get("status") != 200]


def _out(gate: str, passed: bool, detail: str, **measured: Any) -> dict:
    return {"gate": gate, "passed": bool(passed), "detail": detail,
            "measured": measured}


def _nm(gate: str, reason: str, **measured: Any) -> dict:
    return {"gate": gate, "passed": None, "detail": reason, "measured": measured}


# --------------------------------------------------------------------------- #
# per-question gates
# --------------------------------------------------------------------------- #


def authority_recall(question: dict, queries: list[dict], min_len: int = 6) -> list[dict]:
    slug = question["slug"]
    authority_ids = list(question.get("authority_ids") or [])
    out: list[dict] = []
    if not authority_ids:
        reason = ("frozen reality benchmark carries no controlling-authority set "
                  "for this question (authority_ids = []); recall is not measurable "
                  "and is never counted as a pass")
        for gate in [f"authority::baseline_recall::{slug}"] + [
            f"authority::baseline_lang_recall::{slug}::{lang}"
            for lang in frozen.LANGUAGES
        ]:
            out.append(_nm(gate, reason, required=authority_ids))
        return out

    for lang in frozen.LANGUAGES:
        rows = _pool(queries, slug=slug, channel="baseline", language=lang)
        matched = match_authorities(authority_ids, rows, min_len=min_len)
        hits = sorted(a for a, core in matched.items() if core)
        failed = _failed_queries(queries, slug=slug)
        detail = ""
        if not hits:
            detail = (f"no frozen controlling authority in the {lang} baseline top-k "
                      f"(missing: {sorted(set(authority_ids) - set(hits))}")
            if failed:
                detail += f"; transport failures: {failed}"
            detail += ")"
        out.append(_out(
            f"authority::baseline_lang_recall::{slug}::{lang}", bool(hits), detail,
            required=authority_ids, hits=hits,
            missing=sorted(set(authority_ids) - set(hits)),
            n_rows=len(rows), transport_failures=failed))

    union_rows = _pool(queries, slug=slug, channel="baseline")
    matched = match_authorities(authority_ids, union_rows, min_len=min_len)
    hits = sorted(a for a, core in matched.items() if core)
    missing = sorted(set(authority_ids) - set(hits))
    failed = _failed_queries(queries, slug=slug)
    detail = ""
    if not hits:
        detail = f"no frozen controlling authority in the FR/DE/IT baseline union (missing: {missing})"
        if failed:
            detail += f"; transport failures: {failed}"
    out.append(_out(
        f"authority::baseline_recall::{slug}", bool(hits), detail,
        required=authority_ids, hits=hits, missing=missing,
        n_rows=len(union_rows), transport_failures=failed))
    return out


def norm_retrievable(question: dict, queries: list[dict]) -> dict:
    slug = question["slug"]
    tokens = [frozen.normalize_text(t) for t in question["queries"].get("norm_tokens") or []]
    rows = _pool(queries, slug=slug)
    evidence = []
    for row in rows:
        text = frozen.normalize_text(row.get("text_head"))
        hit = next((t for t in tokens if t and t in text), None)
        if hit:
            evidence.append({"decision_id": row.get("decision_id"),
                             "canonical_url": row.get("canonical_url"),
                             "token": hit})
            if len(evidence) >= 3:
                break
    return _out(
        f"norm::retrievable::{slug}", bool(evidence),
        "" if evidence else f"no retrieved row text contains any frozen norm token {tokens}",
        tokens=tokens, n_rows=len(rows), evidence=evidence)


def known_counter_recall(question: dict, queries: list[dict]) -> dict:
    slug = question["slug"]
    known = [c["id"] for c in question.get("known_counter_ids") or []]
    if not known:
        return _nm(f"counter::known_counter_recall::{slug}",
                   "no accepted leg of this question carries a counter-classified "
                   "decision id; known-counter recall is not measurable")
    rows = _pool(queries, slug=slug)
    matched = match_authorities(known, rows)
    hits = sorted(a for a, core in matched.items() if core)
    missing = sorted(set(known) - set(hits))
    return _out(
        f"counter::known_counter_recall::{slug}", bool(hits),
        "" if hits else f"no known counter authority retrieved (missing: {missing})",
        required=known, hits=hits, missing=missing, n_rows=len(rows))


def limiting_marker_verified(question: dict, queries: list[dict]) -> dict:
    slug = question["slug"]
    norm_tokens = [frozen.normalize_text(t)
                   for t in question["queries"].get("norm_tokens") or []]
    limit_tokens = [frozen.normalize_text(t)
                    for t in question["queries"].get("limitation_tokens") or []]
    rows = _pool(queries, slug=slug, channel="counter")
    evidence: list[dict] = []
    for row in rows:
        text = frozen.normalize_text(row.get("text_head"))
        norm_hit = next((t for t in norm_tokens if t and t in text), None)
        lim_hit = next((t for t in limit_tokens if t and t in text), None)
        if norm_hit and lim_hit:
            evidence.append({
                "decision_id": row.get("decision_id"),
                "canonical_url": row.get("canonical_url"),
                "norm_token": norm_hit,
                "limitation_token": lim_hit,
                "text_head": str(row.get("text_head") or "")[:240],
            })
            if len(evidence) >= 3:
                break
    return _out(
        f"counter::limiting_marker_verified::{slug}", bool(evidence),
        "" if evidence else
        ("no counter-channel row text contains both a frozen norm token and a "
         f"frozen limitation token (norm {norm_tokens}, limitation {limit_tokens})"),
        norm_tokens=norm_tokens, limitation_tokens=limit_tokens,
        n_counter_rows=len(rows), evidence=evidence)


def source_rows_valid(question: dict, queries: list[dict]) -> dict:
    slug = question["slug"]
    rows = _pool(queries, slug=slug)
    offenders: list[dict] = []
    n_bad = 0
    for row in rows:
        url = str(row.get("canonical_url") or "")
        parsed = urlparse(url)
        reasons = []
        if not str(row.get("decision_id") or "").strip():
            reasons.append("empty decision_id")
        if parsed.scheme != "https" or parsed.hostname != "mcp.opencaselaw.ch":
            reasons.append(f"canonical_url host/scheme: {url[:60]}")
        if str(row.get("language") or "") not in frozen.LANGUAGES:
            reasons.append(f"language {row.get('language')!r}")
        if reasons:
            n_bad += 1
            if len(offenders) < 8:
                offenders.append({"decision_id": row.get("decision_id"),
                                  "canonical_url": url[:80], "reasons": reasons})
    return _out(
        f"source::rows_valid::{slug}", n_bad == 0,
        "" if n_bad == 0 else f"{n_bad} of {len(rows)} retrieved rows fail source validity",
        n_rows=len(rows), n_offenders=n_bad, offenders=offenders)


def unique_ids(question: dict, queries: list[dict]) -> dict:
    slug = question["slug"]
    dupes: list[dict] = []
    n_checked = 0
    for q in queries:
        if q.get("slug") != slug or q.get("status") != 200:
            continue
        n_checked += 1
        seen: dict[str, str] = {}
        for row in q.get("rows") or []:
            # sorted() keeps the example order deterministic across processes
            # (set iteration order varies with PYTHONHASHSEED).
            for core in sorted(row_cores(row)):
                if core in seen and len(dupes) < 8:
                    dupes.append({"query_key": q.get("query_key"),
                                  "core": core, "ids": [seen[core],
                                                        row.get("decision_id")]})
                seen.setdefault(core, str(row.get("decision_id") or ""))
    return _out(
        f"duplicate::unique_ids::{slug}", not dupes,
        "" if not dupes else f"duplicate alnum-core ids within query responses: {dupes[:4]}",
        n_queries_checked=n_checked, examples=dupes)


# --------------------------------------------------------------------------- #
# global gates
# --------------------------------------------------------------------------- #


def transport_ok(spec: dict, queries: list[dict]) -> dict:
    failed = [{"query_key": q.get("query_key"), "status": q.get("status"),
               "error": str(q.get("error"))[:160]}
              for q in queries if q.get("status") != 200]
    return _out("transport::all_queries_ok", not failed,
                "" if not failed else f"{len(failed)} of {len(queries)} searches failed transport",
                n_queries=len(queries), failures=failed)


#: The only pass-A mode under which wall-clock latency is a measurement at all.
#:
#: REPLAY/LIVE SEPARATION (cycle 38945976309).  Content gates may legitimately be
#: satisfied from the committed response cache: replaying the same raw bytes is a
#: reproducibility check, and it is what makes this benchmark re-runnable without
#: network.  Wall-clock latency is NOT such a property.  A cached replay measures
#: the disk, so before this rule the recorded negative finding
#: ``latency::full_pass_under_budget`` FAIL (256.827s >= 240s) silently became a
#: PASS on a plain ``--offline`` re-run of the SAME record's data, with no gate
#: reporting the substitution.  That is a false green on a claim-bearing gate and
#: the exact re-run the cycle report recommends.  A latency gate may therefore
#: only return a pass/fail verdict when pass A was a live pass; otherwise it is
#: ``not_measurable`` with an explicit reason and is never counted as a pass.
#: This changes no budget and no threshold; it only refuses to let a replay
#: stand in for a measurement.
LIVE_PASS_MODE = "live"


def _pass_a_not_live(record: dict) -> str:
    """Reason string when pass A was not a live pass (empty string when it was)."""
    mode = record.get("pass_a_mode")
    if mode == LIVE_PASS_MODE:
        return ""
    return (
        f"pass_a_mode={mode!r} is not {LIVE_PASS_MODE!r}: wall-clock latency is only "
        "measurable on a live pass; a cached replay measures the disk. Re-run the "
        "live pass (or --rescore the live record) to obtain a latency verdict."
    )


def search_latency(spec: dict, queries: list[dict], record: dict | None = None) -> dict:
    budget = float(spec["latency_budgets"]["per_search_seconds"])
    if record is not None:
        reason = _pass_a_not_live(record)
        if reason:
            return _nm("latency::search_under_budget", reason)
    latencies = [q["latency_seconds"] for q in queries
                 if q.get("status") == 200 and isinstance(q.get("latency_seconds"), (int, float))]
    if not latencies:
        return _nm("latency::search_under_budget", "no successful search carries a latency")
    worst = max(latencies)
    return _out("latency::search_under_budget", worst < budget,
                "" if worst < budget else f"slowest search {worst}s >= {budget}s budget",
                worst_seconds=worst, budget_seconds=budget, n_measured=len(latencies))


def full_pass_latency(spec: dict, record: dict) -> dict:
    budget = float(spec["latency_budgets"]["full_pass_seconds"])
    reason = _pass_a_not_live(record)
    if reason:
        return _nm("latency::full_pass_under_budget", reason)
    wall = record.get("pass_a_wall_seconds")
    if wall is None:
        return _nm("latency::full_pass_under_budget", "record carries no live-pass wall time")
    return _out("latency::full_pass_under_budget", float(wall) < budget,
                "" if float(wall) < budget else f"live pass {wall}s >= {budget}s budget",
                wall_seconds=wall, budget_seconds=budget)


def reproducible(spec: dict, record: dict) -> dict:
    live = {q.get("query_key"): q for q in record.get("queries") or []}
    replay = {e.get("query_key"): e for e in
              (record.get("reproducibility") or {}).get("pass_b") or []}
    if not replay:
        return _nm("reproducible::cached_second_pass_identical",
                   "no offline replay pass recorded")
    mismatched: list[dict] = []
    missing: list[str] = []
    for key, q in live.items():
        entry = replay.get(key)
        if entry is None:
            missing.append(key)
            continue
        if (entry.get("raw_sha256") != q.get("raw_sha256")
                or entry.get("ids_sha256") != q.get("ids_sha256")):
            mismatched.append({"query_key": key,
                               "live_sha": q.get("raw_sha256"),
                               "replay_sha": entry.get("raw_sha256")})
    problems = bool(mismatched or missing)
    detail = ""
    if problems:
        detail = (f"{len(mismatched)} byte/ids mismatches, {len(missing)} missing replays"
                  if mismatched or missing else "")
        if mismatched:
            detail += f"; first mismatch {mismatched[0]['query_key']}"
    return _out("reproducible::cached_second_pass_identical", not problems, detail,
                n_replayed=len(replay), mismatches=mismatched, missing=missing)


# --------------------------------------------------------------------------- #
# verdict
# --------------------------------------------------------------------------- #


def evaluate(spec: dict, record: dict) -> dict:
    """Pure function: frozen spec + run record -> verdict (deterministic)."""
    questions = frozen.question_by_slug(spec)
    queries = record.get("queries") or []
    min_len = int((spec.get("id_match_rules") or {}).get("min_core_length", 6))
    gates: list[dict] = []
    per_slug: dict[str, dict] = {}

    for slug in frozen.SLUG_ORDER:
        question = questions[slug]
        slug_gates = []
        slug_gates += authority_recall(question, queries, min_len=min_len)
        slug_gates.append(norm_retrievable(question, queries))
        slug_gates.append(known_counter_recall(question, queries))
        slug_gates.append(limiting_marker_verified(question, queries))
        slug_gates.append(source_rows_valid(question, queries))
        slug_gates.append(unique_ids(question, queries))
        gates += slug_gates
        failed = [g["gate"] for g in slug_gates if g["passed"] is False]
        nm = [g["gate"] for g in slug_gates if g["passed"] is None]
        per_slug[slug] = {"n_gates": len(slug_gates), "failed": failed,
                          "not_measurable": nm, "passed": not failed}

    global_gates = [
        transport_ok(spec, queries),
        search_latency(spec, queries, record),
        full_pass_latency(spec, record),
        reproducible(spec, record),
    ]
    gates += global_gates

    failed = [g["gate"] for g in gates if g["passed"] is False]
    not_measurable = [g["gate"] for g in gates if g["passed"] is None]
    passed = [g["gate"] for g in gates if g["passed"] is True]
    return {
        "schema": "lex-retrieval-verdict/1",
        "frozen_sha256": frozen.FROZEN_SHA256,
        "n_gates": len(gates),
        "n_passed": len(passed),
        "n_failed": len(failed),
        "n_not_measurable": len(not_measurable),
        "failed_gates": failed,
        "not_measurable_gates": not_measurable,
        "not_measurable_reasons": {g["gate"]: g["detail"] for g in gates
                                   if g["passed"] is None},
        "per_slug": per_slug,
        "gates": gates,
        "overall_pass": not failed,
        "claim_ceiling": spec.get("claim_ceiling"),
    }


def verdict_sha256(verdict: dict) -> str:
    payload = json.dumps(verdict, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


# --------------------------------------------------------------------------- #
# record-level latency plausibility (cycle 38945976309)
# --------------------------------------------------------------------------- #


def record_latency_plausibility(record: dict) -> list[str]:
    """Cross-checks a record's ``pass_a_wall_seconds`` against its own timestamps.

    The replay/live rule above only binds what the record DECLARES. A record that
    claims ``pass_a_mode: "live"`` while carrying a hand-edited wall time would
    still be scored against the budget and could pass. This closes that gap
    without touching the verdict: on a live sequential pass the wall time cannot
    be shorter than the sum of the per-search latencies it contains, and cannot
    exceed the interval between the pass start and the record's ``generated_at``.

    Returns a list of problems; empty means the latency claim is self-consistent.
    Deliberately a separate function, not a gate: adding a gate would change the
    recorded 38939239917 verdict and destroy its byte-identity test.
    """
    problems: list[str] = []
    if record.get("pass_a_mode") != LIVE_PASS_MODE:
        return problems
    wall = record.get("pass_a_wall_seconds")
    if not isinstance(wall, (int, float)):
        return [f"live record carries no numeric pass_a_wall_seconds ({wall!r})"]

    latencies = [q["latency_seconds"] for q in record.get("queries") or []
                 if isinstance(q.get("latency_seconds"), (int, float))
                 and not q.get("from_cache")]
    if latencies:
        total = round(sum(latencies), 3)
        if float(wall) + 1e-9 < total:
            problems.append(
                f"pass_a_wall_seconds {wall}s is shorter than the sum of the "
                f"{len(latencies)} live search latencies it contains ({total}s); "
                "a sequential live pass cannot be faster than its parts")

    started, generated = record.get("started_at"), record.get("generated_at")
    elapsed = _utc_span_seconds(started, generated)
    if elapsed is not None and float(wall) > elapsed + 1e-6:
        problems.append(
            f"pass_a_wall_seconds {wall}s exceeds the whole record's own "
            f"started_at->generated_at span ({elapsed}s)")
    return problems


def _utc_span_seconds(started: object, generated: object) -> float | None:
    def parse(value: object) -> float | None:
        text = str(value or "")
        if not text:
            return None
        try:
            return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=timezone.utc).timestamp()
        except ValueError:
            return None
    a, b = parse(started), parse(generated)
    if a is None or b is None or b < a:
        return None
    return round(b - a, 3)
