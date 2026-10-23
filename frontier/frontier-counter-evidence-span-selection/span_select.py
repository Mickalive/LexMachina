"""Deterministic extract-verify-abstain counter-evidence span selector.

Charter: ``frontier-counter-evidence-span-selection`` v1 (run 39986101767).

This module is a pure function of (row, frozen rules, question anchor profile)
and the FROZEN span limits declared in ``results/frontier/.../PROTOCOL.json``.
It never calls a model, the network, the clock or a random source.

What it does
------------
For one promoted counter-proposal row, it searches the row's OWN retrieved
``full_text`` for the shortest contiguous passage (1..4 sentence/newline units,
40..700 chars) that passes the frozen classifier's evidence gate:

  * a frozen counter-intent marker for the row's language,
  * a DOMAIN-tier anchor of the row's own question,
  * a PIVOT-tier anchor of the row's own question (so criterion (v) cannot
    fail on the selected span),
  * no frozen polarity-inversion regex,
  * no frozen fragment-pointer pattern.

If such a passage exists, it returns the VERBATIM quote and its character
offsets after proving ``full_text[start:end] == quote``.  Otherwise it returns
an explicit, counted ABSTAIN with a deterministic reason code.  There is no
fallback: a missing or non-verbatim quote is never emitted.

Claim ceiling
-------------
This is a mechanical span-selection measurement over already-retrieved text.
It NEVER asserts that any decision IS supporting, contrary or limiting.  It
changes no rubric, threshold, verdict class, bar or packet; it adds no
retrieval and no model call.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

#: Frozen protocol limits (results/frontier/.../PROTOCOL.json span_rule.limits).
DEFAULT_MIN_SPAN_CHARS = 40
DEFAULT_MAX_SPAN_CHARS = 700
DEFAULT_MAX_WINDOW_UNITS = 4

#: Frozen abstain reason codes, in protocol precedence order.
REASON_NO_RETRIEVED_TEXT = "no_retrieved_text"
REASON_LANGUAGE_NOT_EXPECTED = "language_not_expected"
REASON_FOREIGN_LEGAL_AREA = "foreign_legal_area"
REASON_NO_INTENT_MARKER = "no_intent_marker_in_retrieved_text"
REASON_NO_DOMAIN_ANCHOR = "no_domain_anchor_in_retrieved_text"
REASON_NO_PIVOT_ANCHOR = "no_pivot_anchor_in_retrieved_text"
REASON_POLARITY_INVERTED = "polarity_inverted_in_retrieved_text"
REASON_NO_QUALIFYING_SPAN = "no_qualifying_span"

REASON_PRECEDENCE = (
    REASON_NO_RETRIEVED_TEXT,
    REASON_LANGUAGE_NOT_EXPECTED,
    REASON_FOREIGN_LEGAL_AREA,
    REASON_NO_INTENT_MARKER,
    REASON_NO_DOMAIN_ANCHOR,
    REASON_NO_PIVOT_ANCHOR,
    REASON_POLARITY_INVERTED,
    REASON_NO_QUALIFYING_SPAN,
)

#: Statuses the frozen rubric scores.  Kept here so the selector does not import
#: the product package (which imports numpy at package import time).
SCORED_STATUSES = (
    "candidate-limiting",
    "candidate-contrary",
    "contrary_or_exception",
    "limiting",
)

REPAIR_ID = "heuristic_proposal_promotion_v1"

#: A sentence boundary: punctuation (plus optional closing quote/bracket)
#: followed by whitespace and an upper-case / opening character.  We keep the
#: cut position at the start of the whitespace so the punctuation stays in the
#: preceding unit.
_SENTENCE_CUT = re.compile(r'[.!?;](?:["\'\)\]]*)(\s+)')
_PARAGRAPH_CUT = re.compile(r"\n\s*\n+")
_UPPER_OR_OPEN = set('"\'([«“‘')


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Passage:
    start: int
    end: int


@dataclass
class SpanDecision:
    """The selector's per-row output (JSON-serialisable)."""

    decision_id: str
    evidenced: bool
    quote: str
    char_start: int | None
    char_end: int | None
    reason_code: str
    full_text_sha256: str
    full_text_len: int
    language: str
    legal_area: str
    intent_marker: str | None
    domain_anchor: str | None
    pivot_anchor: str | None
    window_passage_count: int
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "evidenced": self.evidenced,
            "quote": self.quote,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "reason_code": self.reason_code,
            "full_text_sha256": self.full_text_sha256,
            "full_text_len": self.full_text_len,
            "language": self.language,
            "legal_area": self.legal_area,
            "intent_marker": self.intent_marker,
            "domain_anchor": self.domain_anchor,
            "pivot_anchor": self.pivot_anchor,
            "window_passage_count": self.window_passage_count,
            "diagnostics": self.diagnostics,
        }


def _lang_of(row: dict[str, Any]) -> str:
    lang = str(row.get("language") or "").lower()
    return lang if lang in ("de", "fr", "it") else "de"


def _trim(text: str, start: int, end: int) -> tuple[int, int]:
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def _split_long_segment(text: str, start: int, end: int, max_chars: int) -> Iterable[Passage]:
    """Split an over-long segment at whitespace, deterministically."""
    pos = start
    while pos < end:
        if end - pos <= max_chars:
            s, e = _trim(text, pos, end)
            if e > s:
                yield Passage(s, e)
            break
        limit = pos + max_chars
        # Prefer the last whitespace inside the limit; hard-cut otherwise.
        cut = text.rfind(" ", pos + 1, limit + 1)
        if cut <= pos:
            cut = limit
        s, e = _trim(text, pos, cut)
        if e > s:
            yield Passage(s, e)
        pos = cut
        while pos < end and text[pos].isspace():
            pos += 1


def split_passages(text: str, max_chars: int = DEFAULT_MAX_SPAN_CHARS) -> list[Passage]:
    """Split ``text`` into trimmed passage units of at most ``max_chars``.

    Boundaries are paragraph breaks (blank lines) and sentence punctuation
    followed by whitespace + upper-case/opening character.  The cut points are
    deterministic and depend only on the input bytes.
    """
    if not text:
        return []
    cuts: list[tuple[int, int]] = []
    for m in _SENTENCE_CUT.finditer(text):
        nxt = text[m.end() : m.end() + 1]
        if not nxt or nxt.isupper() or nxt in _UPPER_OR_OPEN:
            # cut_start = start of the whitespace run; cut_end = end of it.
            cuts.append((m.start(1), m.end(1)))
    for m in _PARAGRAPH_CUT.finditer(text):
        cuts.append((m.start(), m.end()))
    cuts.sort()

    units: list[Passage] = []
    seg_start = 0
    for cut_start, cut_end in cuts:
        if cut_start < seg_start:
            if cut_end > seg_start:
                seg_start = cut_end
            continue
        if cut_start > seg_start:
            s, e = _trim(text, seg_start, cut_start)
            if e > s:
                units.extend(_split_long_segment(text, s, e, max_chars))
        seg_start = max(seg_start, cut_end)
    if seg_start < len(text):
        s, e = _trim(text, seg_start, len(text))
        if e > s:
            units.extend(_split_long_segment(text, s, e, max_chars))
    return units


def iter_windows(
    units: Sequence[Passage],
    min_chars: int = DEFAULT_MIN_SPAN_CHARS,
    max_chars: int = DEFAULT_MAX_SPAN_CHARS,
    max_units: int = DEFAULT_MAX_WINDOW_UNITS,
) -> Iterable[Passage]:
    """Yield every contiguous window of 1..``max_units`` units within limits."""
    n = len(units)
    for i in range(n):
        for j in range(i + 1, min(n, i + max_units) + 1):
            start = units[i].start
            end = units[j - 1].end
            length = end - start
            if length < min_chars:
                continue
            if length > max_chars:
                break
            yield Passage(start, end)


def verify_span(full_text: str, quote: str, start: int | None, end: int | None) -> bool:
    """True iff ``quote`` is exactly the character slice and occurs verbatim."""
    if not quote or start is None or end is None:
        return False
    if start < 0 or end > len(full_text) or start >= end:
        return False
    return full_text[start:end] == quote and quote in full_text


def _hits(nz: Any, tokens: list[str], terms: Sequence[str], *, anchor: bool) -> list[str]:
    out: list[str] = []
    for term in terms or ():
        hit = nz.match_anchor(tokens, term) if anchor else nz.match_marker(tokens, term)
        if hit is not None and hit not in out:
            out.append(hit)
    return sorted(out)


def _rx_hits(nz: Any, rx_text: str, patterns: Sequence[str]) -> list[str]:
    out: list[str] = []
    for pat in patterns or ():
        if nz.match_regex(rx_text, pat) is not None and pat not in out:
            out.append(pat)
    return sorted(out)


def _abstain(
    *,
    row: dict[str, Any],
    full_text: str,
    language: str,
    legal_area: str,
    reason_code: str,
    diagnostics: dict[str, Any],
) -> SpanDecision:
    return SpanDecision(
        decision_id=str(row.get("decision_id") or ""),
        evidenced=False,
        quote="",
        char_start=None,
        char_end=None,
        reason_code=reason_code,
        full_text_sha256=sha256_text(full_text),
        full_text_len=len(full_text),
        language=language,
        legal_area=legal_area,
        intent_marker=None,
        domain_anchor=None,
        pivot_anchor=None,
        window_passage_count=0,
        diagnostics=diagnostics,
    )


def select_span(
    row: dict[str, Any],
    rules: Any,
    profile: dict[str, Any],
    *,
    min_chars: int = DEFAULT_MIN_SPAN_CHARS,
    max_chars: int = DEFAULT_MAX_SPAN_CHARS,
    max_units: int = DEFAULT_MAX_WINDOW_UNITS,
) -> SpanDecision:
    """Select and verify one counter-evidence quote, or abstain.

    ``rules`` is the frozen ``FrozenRules`` object; ``profile`` is the row's own
    question anchor profile from ``rules.question_anchors``.
    """
    text = str(row.get("full_text") or "")
    language = _lang_of(row)
    legal_area = str(row.get("legal_area") or "")
    expected_languages = list(profile.get("expected_languages") or [])
    foreign_areas = list(profile.get("foreign_legal_area_fields") or [])

    base_diag: dict[str, Any] = {
        "expected_languages": expected_languages,
        "foreign_legal_area_fields": foreign_areas,
        "min_chars": min_chars,
        "max_chars": max_chars,
        "max_window_units": max_units,
    }

    if not text.strip():
        return _abstain(
            row=row, full_text=text, language=language, legal_area=legal_area,
            reason_code=REASON_NO_RETRIEVED_TEXT,
            diagnostics={**base_diag, "full_text_present": False},
        )
    if expected_languages and language not in expected_languages:
        return _abstain(
            row=row, full_text=text, language=language, legal_area=legal_area,
            reason_code=REASON_LANGUAGE_NOT_EXPECTED,
            diagnostics={**base_diag, "language_ok": False},
        )
    if legal_area in foreign_areas:
        return _abstain(
            row=row, full_text=text, language=language, legal_area=legal_area,
            reason_code=REASON_FOREIGN_LEGAL_AREA,
            diagnostics={**base_diag, "legal_area_ok": False},
        )

    nz = rules.normalizer
    lex = rules.lexicons
    markers = rules.marker_lexicon(language, "primary")
    inversion = list(lex["polarity_inversion"].get(language) or [])
    pointer = list(lex["fragment_pointer"] or [])
    procedural = list(lex["procedural_formula"].get(language) or [])
    outcome = list(lex["procedural_outcome_words"].get(language) or [])
    domain = list(profile.get("domain") or [])
    pivot = list(profile.get("pivot") or [])

    whole_tokens = nz.stems(text)
    whole_marker_hits = _hits(nz, whole_tokens, markers, anchor=False)
    whole_domain_hits = _hits(nz, whole_tokens, domain, anchor=True)
    whole_pivot_hits = _hits(nz, whole_tokens, pivot, anchor=True)

    units = split_passages(text, max_chars)
    candidates: list[dict[str, Any]] = []
    qualified_windows = 0
    inverted_qualified_windows = 0
    pointer_qualified_windows = 0

    for window in iter_windows(units, min_chars, max_chars, max_units):
        quote = text[window.start : window.end]
        if not verify_span(text, quote, window.start, window.end):
            continue
        ev_rx = nz.regex_text(quote)
        ev_tokens = nz.stems(quote)
        marker_hits = _hits(nz, ev_tokens, markers, anchor=False)
        domain_hits = _hits(nz, ev_tokens, domain, anchor=True)
        pivot_hits = _hits(nz, ev_tokens, pivot, anchor=True)
        if not (marker_hits and domain_hits and pivot_hits):
            continue
        qualified_windows += 1
        inversion_hits = _rx_hits(nz, ev_rx, inversion)
        if inversion_hits:
            inverted_qualified_windows += 1
            continue
        pointer_hits = _rx_hits(nz, nz.regex_text(quote).strip(), pointer)
        if pointer_hits:
            pointer_qualified_windows += 1
            continue
        procedural_hits = _rx_hits(nz, ev_rx, procedural)
        outcome_hits = _hits(nz, ev_tokens, outcome, anchor=False)
        if procedural_hits and not outcome_hits and not marker_hits:
            continue
        candidates.append({
            "start": window.start,
            "end": window.end,
            "quote": quote,
            "intent_marker": marker_hits[0],
            "intent_markers": marker_hits,
            "domain_anchor": domain_hits[0],
            "domain_anchors": domain_hits,
            "pivot_anchor": pivot_hits[0],
            "pivot_anchors": pivot_hits,
            "passage_count": sum(
                1 for u in units if u.start >= window.start and u.end <= window.end
            ),
        })

    diag = {
        **base_diag,
        "n_passages": len(units),
        "whole_text_intent_markers": whole_marker_hits,
        "whole_text_domain_anchors": whole_domain_hits,
        "whole_text_pivot_anchors": whole_pivot_hits,
        "qualified_windows": qualified_windows,
        "inverted_qualified_windows": inverted_qualified_windows,
        "pointer_qualified_windows": pointer_qualified_windows,
    }

    if candidates:
        best = min(candidates, key=lambda c: (len(c["quote"]), c["start"], c["end"]))
        return SpanDecision(
            decision_id=str(row.get("decision_id") or ""),
            evidenced=True,
            quote=best["quote"],
            char_start=best["start"],
            char_end=best["end"],
            reason_code="supported",
            full_text_sha256=sha256_text(text),
            full_text_len=len(text),
            language=language,
            legal_area=legal_area,
            intent_marker=best["intent_marker"],
            domain_anchor=best["domain_anchor"],
            pivot_anchor=best["pivot_anchor"],
            window_passage_count=best["passage_count"],
            diagnostics={
                **diag,
                "intent_markers": best["intent_markers"],
                "domain_anchors": best["domain_anchors"],
                "pivot_anchors": best["pivot_anchors"],
            },
        )

    # Deterministic reason precedence, computed from the whole retrieved text.
    if not whole_marker_hits:
        reason = REASON_NO_INTENT_MARKER
    elif not whole_domain_hits:
        reason = REASON_NO_DOMAIN_ANCHOR
    elif not whole_pivot_hits:
        reason = REASON_NO_PIVOT_ANCHOR
    elif qualified_windows > 0 and inverted_qualified_windows == qualified_windows:
        reason = REASON_POLARITY_INVERTED
    else:
        reason = REASON_NO_QUALIFYING_SPAN
    return _abstain(
        row=row, full_text=text, language=language, legal_area=legal_area,
        reason_code=reason, diagnostics=diag,
    )


def apply_span_selection(
    bundle: dict[str, Any],
    rules: Any,
    profile: dict[str, Any],
    *,
    qid: str | None = None,
    min_chars: int = DEFAULT_MIN_SPAN_CHARS,
    max_chars: int = DEFAULT_MAX_SPAN_CHARS,
    max_units: int = DEFAULT_MAX_WINDOW_UNITS,
) -> tuple[dict[str, Any], list[SpanDecision]]:
    """Return a NEW bundle with verified quotes on promoted rows.

    Only rows carrying ``counter_proposal_source ==
    heuristic_proposal_promotion_v1`` and a frozen scored status are touched.
    ``counter_status`` is NEVER changed, so the frozen scorer's denominator is
    preserved.  An abstained row keeps its proposed status and gets an empty
    ``counter_evidence``; ``counter_evidence_span`` is null and the reason lives
    in ``counter_span_selection``, so the accepted classifier can count the
    abstention rather than score stale text.
    """
    import copy

    out = copy.deepcopy(bundle)
    decisions: list[SpanDecision] = []
    for d in out.get("decisions") or []:
        if str(d.get("counter_proposal_source") or "") != REPAIR_ID:
            continue
        if str(d.get("counter_status") or "") not in SCORED_STATUSES:
            continue
        dec = select_span(
            d, rules, profile,
            min_chars=min_chars, max_chars=max_chars, max_units=max_units,
        )
        decisions.append(dec)
        if dec.evidenced:
            d["counter_evidence"] = dec.quote
            d["counter_evidence_verified"] = True
            d["counter_evidence_source"] = "retrieved_full_text"
            d["counter_evidence_span"] = {
                "decision_id": dec.decision_id,
                "quote": dec.quote,
                "char_start": dec.char_start,
                "char_end": dec.char_end,
                "intent_marker": dec.intent_marker,
                "domain_anchor": dec.domain_anchor,
                "pivot_anchor": dec.pivot_anchor,
                "window_passage_count": dec.window_passage_count,
                "full_text_sha256": dec.full_text_sha256,
            }
            d["counter_span_selection"] = {
                "abstained": False,
                "reason_code": dec.reason_code,
            }
            d.pop("counter_evidence_span_abstain_reason", None)
        else:
            d["counter_evidence"] = ""
            d["counter_evidence_verified"] = False
            d["counter_evidence_source"] = "span_selection_abstained"
            d["counter_evidence_span"] = None
            d["counter_span_selection"] = {
                "abstained": True,
                "reason_code": dec.reason_code,
                "diagnostics": dec.diagnostics,
            }
            d.pop("counter_evidence_span_abstain_reason", None)

    prov = out.setdefault("provenance", {}).setdefault("counter_evidence_span_selection", {})
    prov.update({
        "component": "frontier-counter-evidence-span-selection",
        "charter_version": 1,
        "rule": "deterministic_extract_verify_abstain_v1",
        "qid": qid,
        "n_promoted_rows": len(decisions),
        "n_evidenced": sum(1 for d in decisions if d.evidenced),
        "n_abstained": sum(1 for d in decisions if not d.evidenced),
        "selector_abstention_reasons": count_reasons(decisions),
        "limits": {"min_chars": min_chars, "max_chars": max_chars, "max_units": max_units},
        "claim_ceiling": (
            "Mechanical span selection over already-retrieved full_text. This "
            "component NEVER asserts that any decision IS supporting, contrary or "
            "limiting; it selects a verbatim passage that passes the frozen "
            "evidence gate or abstains."
        ),
    })
    return out, decisions


def count_reasons(decisions: Sequence[SpanDecision]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for d in decisions:
        if d.evidenced:
            continue
        counts[d.reason_code] = counts.get(d.reason_code, 0) + 1
    return dict(sorted(counts.items()))


__all__ = [
    "DEFAULT_MAX_SPAN_CHARS",
    "DEFAULT_MAX_WINDOW_UNITS",
    "DEFAULT_MIN_SPAN_CHARS",
    "Passage",
    "REASON_PRECEDENCE",
    "REPAIR_ID",
    "SCORED_STATUSES",
    "SpanDecision",
    "count_reasons",
    "apply_span_selection",
    "iter_windows",
    "select_span",
    "sha256_text",
    "split_passages",
    "verify_span",
]
