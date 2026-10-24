"""Verbatim counter-evidence span selection (product-owned, direction v65).

Why this module exists
----------------------
The accepted BOUNDED-NEGATIVE verdict on packet-of-record v3 names three bounded
causes.  The first is an **emission-path** cause: after the accepted emission
repair the frozen classifier sees 8/8/4 scored counter rows and emits **none**
(``pivot_absent`` / ``no_intent_marker`` / ``no_domain_anchor``).  The frozen
charter's own proposed first remedy is an *extract-verify-abstain* step: the
quote shown as counter evidence must (a) appear **verbatim** in the decision
text, (b) carry an intent marker and (c) carry a domain anchor; otherwise the
row abstains.

The incumbent path forwards whatever short evidence string the adversarial
stage happened to surface (often a snippet or a regenerated sentence that is
not a substring of the raw text).  This module selects a span from the row's
own text and lets the **already-accepted, frozen** ``decide_label`` gate decide.
It does not re-score, re-tune or re-derive that gate:

* the span must be a byte-exact substring of a named text field (verified with
  offsets and a sha256 of the field);
* the span is chosen ONLY if ``decide_label(row, frozen_rules, profile)``
  returns a non-abstained decision for it;
* if no span emits, the row keeps its baseline decision and abstains exactly as
  before.

Selection is deterministic: fields are visited in a fixed order
(``full_text``, ``regeste``, ``snippet``, ``title``), sentences in text order,
and the first emitting span wins.  No network, no model, no randomness.

Claim ceiling (inherited from the accepted classifier)
------------------------------------------------------
This seam selects and verifies the QUOTE, and reports the classifier's
confirm-or-abstain outcome.  It NEVER asserts that a specific decision IS
supporting, contrary or limiting.  The emitted label is still the row's own
proposed label, merely confirmed against a verbatim span.  Scanning several
sentences raises the opportunity for a gate pass, so the count of scanned
sentences and the field scanned are written into provenance for audit; the
support rate, abstention count and yield are published side by side by the
accepted anchor seam.

Kill-switch: ``LEXMACHINA_COUNTER_SPAN=off`` (default ``select``).
"""
from __future__ import annotations

import copy
import hashlib
import os
import re
from dataclasses import dataclass, field as dc_field
from typing import Any, Iterable
from .counter_anchor import (
    SCORED_STATUSES,
    _import_component,
    load_frozen_rules,
    resolve_anchor_profile,
)

SPAN_ENV = "LEXMACHINA_COUNTER_SPAN"
SPAN_GUARD_ENV = "LEXMACHINA_COUNTER_SPAN_GUARD"
MODE_SELECT = "select"
MODE_OFF = "off"

SPAN_VERSION = "counter_span_selection/1"

#: Local sentence boundary for span candidates.  Deliberately NOT
#: ``answer.SENT_SPLIT``: that splitter rewrites newlines and treats a digit
#: after a period as a sentence start, so "Art. 321 OR" is torn in two and the
#: citation-bearing sentence can never be selected as one verbatim span.
SPAN_SPLIT = re.compile(
    r"(?<=[.!?;])\s+(?=[A-ZÄÖÜÉÈÊÀÂÆÇÎÏÔŒÙÛË«\"'])"
)
_ABBREVIATIONS = (
    "art", "abs", "ziff", "lit", "bst", "nr", "s", "ff", "vgl", "bzw",
    "resp", "cf", "ex", "al", "rd", "n", "p", "pp", "marg", "consid",
)

#: Fixed field order.  ``full_text`` is the raw body; the shorter fields are
#: fallbacks for rows that were never hydrated.
TEXT_FIELDS = ("full_text", "regeste", "snippet", "title")

#: Minimum span length, matching the accepted classifier's evidence gate intent.
MIN_SPAN_CHARS = 40

#: Per-field candidate cap.  Bounds the worst case on a 300k-char decision and
#: is part of the frozen selection protocol (reported in provenance).
MAX_CANDIDATES_PER_FIELD = 240

#: Proposal statuses the selector may probe.  It never invents a status: it
#: re-uses the row's own scored status, else the adversarial signal's proposal.
PROPOSAL_FALLBACK = "candidate-limiting"

#: Precision guard vocabulary.  The frozen gate checks marker + broad domain
#: anchor; on real BGE bodies that lets an incidental "nicht" plus a common
#: legal noun pass.  The guard requires the span to be ANCHORED to this query:
#: either a statute/article anchor from the frozen profile, or an exact
#: multi-content-word phrase from the user's own question.  It is lexical and
#: disclosed; it is not a legal-relevance score.
STOPWORDS_FOR_PHRASE = frozenset("""
de du des la le les un une et ou a au aux en dans pour par sur sous avec sans
que qui dont est sont il elle ils elles ce cette ces son sa ses leur leurs the
and of to in for with on at by der die das und den dem ein eine einer eines
einem einen zu zur zum von vom bei mit ohne auf aus als auch nur oder dass sich
ist sind war wird werden di del della dello dei degli delle dal allo alla al ai
agli sul sulla per con come non che e il lo i gli
""".split())

#: Statute/law abbreviations that carry no digit but are still specific enough
#: to anchor a span.  Kept deliberately small; the profile's digit-bearing
#: pivots (``257d``, ``2052`` …) are the primary anchors.
STATUTE_ABBREVIATIONS = frozenset(
    "eog or co cp ldip zpo stpo svg uvg kvg bvg ahv amsl".split()
)


@dataclass(frozen=True)
class SpanCandidate:
    field: str
    start: int
    end: int
    quote: str


def _mode(env: dict[str, str] | None = None) -> str:
    env = os.environ if env is None else env
    raw = str(env.get(SPAN_ENV) or MODE_SELECT).strip().lower()
    if raw in ("", "select", "on", "anchor"):
        return MODE_SELECT
    if raw in (MODE_OFF, "none", "incumbent"):
        return MODE_OFF
    raise ValueError(f"unknown {SPAN_ENV}={raw!r}; known: select, off")


def _normalize_guard(text: str) -> str:
    import unicodedata

    s = unicodedata.normalize("NFKD", str(text or "")).lower()
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def guard_terms(profile: dict, query: str) -> dict[str, Any]:
    """Statute anchors and exact query phrases the span must hit (or both)."""
    statutes: set[str] = set()
    for pivot in (profile or {}).get("pivot") or []:
        norm = _normalize_guard(pivot).replace(" ", "")
        if not norm:
            continue
        if any(ch.isdigit() for ch in norm) or norm in STATUTE_ABBREVIATIONS:
            statutes.add(norm)
    tokens = _normalize_guard(query).split()
    phrases: set[str] = set()
    for n in (2, 3, 4):
        for i in range(len(tokens) - n + 1):
            seq = tokens[i:i + n]
            content = [
                t for t in seq
                if t not in STOPWORDS_FOR_PHRASE and len(t) >= 3
            ]
            if len(content) >= 2:
                phrases.add(" ".join(seq))
    return {
        "statutes": sorted(statutes),
        "phrases": sorted(phrases),
        "available": bool(statutes or phrases),
    }


def _statute_present(statute: str, text: str, tokens: set[str]) -> bool:
    if not statute:
        return False
    if statute in tokens:
        return True
    digits = re.sub(r"\D", "", statute)
    alpha = re.sub(r"\d", "", statute)
    if digits and alpha:
        return digits in tokens and (alpha in tokens or alpha in text)
    return statute in tokens


def span_passes_precision_guard(quote: str, guard: dict[str, Any]) -> bool:
    """True iff the span carries a profile statute or an exact query phrase."""
    if not guard.get("available"):
        # No query-specific anchor could be derived: the caller records this
        # and falls back to the accepted gate rather than inventing a filter.
        return True
    text = _normalize_guard(quote)
    padded = f" {text} "
    tokens = set(text.split())
    for statute in guard.get("statutes") or []:
        if _statute_present(str(statute), text, tokens):
            return True
    for phrase in guard.get("phrases") or []:
        if f" {phrase} " in padded:
            return True
    return False


def sentence_spans(
    text: str,
    *,
    field_name: str = "full_text",
    max_len: int = 600,
    max_candidates: int = MAX_CANDIDATES_PER_FIELD,
) -> list[SpanCandidate]:
    """Split ``text`` into verbatim sentence spans, preserving raw offsets.

    Unlike :func:`product.query.answer.split_sentences`, this never rewrites the
    text (no newline substitution) and returns ``text[start:end] == quote`` by
    construction, so the quote can be verified as a literal substring.  Parts
    torn off after a legal abbreviation (``Art.``, ``Abs.``, ``Ziff.`` …) are
    re-joined before the candidate is emitted.
    """
    raw = str(text or "")
    if not raw:
        return []

    parts: list[tuple[int, int, str]] = []
    pos = 0
    for m in SPAN_SPLIT.finditer(raw):
        part = raw[pos:m.start()]
        if part:
            parts.append((pos, m.start(), part))
        pos = m.end()
    tail = raw[pos:]
    if tail:
        parts.append((pos, len(raw), tail))

    merged: list[tuple[int, int, str]] = []
    for start, end, part in parts:
        if merged and _ends_with_abbreviation(merged[-1][2]):
            pstart = merged[-1][0]
            merged[-1] = (pstart, end, raw[pstart:end])
        else:
            merged.append((start, end, part))

    out: list[SpanCandidate] = []
    for start, end, part in merged:
        stripped = part.strip()
        if len(stripped) <= MIN_SPAN_CHARS:
            continue
        lead = len(part) - len(part.lstrip())
        qstart = start + lead
        quote = stripped[:max_len]
        out.append(SpanCandidate(field_name, qstart, qstart + len(quote), quote))
        if len(out) >= max_candidates:
            break
    return out

def _ends_with_abbreviation(text: str) -> bool:
    tail = str(text or "").rstrip()
    if not tail.endswith("."):
        return False
    word = re.split(r"[^\w]+", tail[:-1].rstrip())[-1].lower()
    return word in _ABBREVIATIONS


def field_candidates(row: dict) -> list[SpanCandidate]:
    """All bounded, deterministic spans over the row's named text fields."""
    out: list[SpanCandidate] = []
    for name in TEXT_FIELDS:
        text = str(row.get(name) or "")
        if not text.strip():
            continue
        out.extend(sentence_spans(text, field_name=name))
    return out


def verify_span(text: str, quote: str, start: int, end: int) -> bool:
    """True iff ``quote`` is the byte-exact slice ``text[start:end]``."""
    try:
        start = int(start)
        end = int(end)
    except (TypeError, ValueError):
        return False
    if start < 0 or end <= start or end > len(text):
        return False
    return text[start:end] == quote


@dataclass
class SpanSelection:
    selected: bool
    reason_code: str
    quote: str = ""
    field: str = ""
    start: int = -1
    end: int = -1
    n_candidates: int = 0
    n_evaluated: int = 0
    decision: Any | None = None
    baseline_label: str | None = None
    baseline_reason: str | None = None
    scanned_fields: list[str] = dc_field(default_factory=list)
    guard_available: bool = True
    n_guard_rejected: int = 0
    #: True iff the row's *incumbent* counter_evidence was rejected by the
    #: deterministic D2/D3/D4 content filter, independent of the frozen gate.
    #: ``baseline_defect`` names the defect class (empty when clean).
    baseline_defect: str = ""
    n_content_rejected: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": SPAN_VERSION,
            "selected": self.selected,
            "verified": bool(self.selected),
            "reason_code": self.reason_code,
            "quote": self.quote,
            "field": self.field,
            "start": self.start,
            "end": self.end,
            "n_candidates": self.n_candidates,
            "n_evaluated": self.n_evaluated,
            "baseline_label": self.baseline_label,
            "baseline_reason": self.baseline_reason,
            "scanned_fields": list(self.scanned_fields),
            "guard_available": self.guard_available,
            "n_guard_rejected": self.n_guard_rejected,
            "baseline_defect": self.baseline_defect,
            "n_content_rejected": self.n_content_rejected,
        }


def _proposal_status(row: dict) -> str:
    status = str(row.get("counter_status") or "")
    if status in SCORED_STATUSES:
        return status
    signal = row.get("adversarial_retrieval_signal") or {}
    proposed = str(signal.get("heuristic_status") or signal.get("proposed_status") or "")
    if proposed in SCORED_STATUSES:
        return proposed
    return PROPOSAL_FALLBACK


def _minimal_row(row: dict, status: str, quote: str) -> dict:
    probe = dict(row)
    probe["counter_status"] = status
    probe["counter_evidence"] = quote
    # A quote is not yet "verified" while the gate is deciding.
    probe["counter_evidence_verified"] = False
    probe.pop("counter_anchor_decision", None)
    probe.pop("counter_anchor_label", None)
    return probe


def _locate_quote(quote: str, row: dict) -> tuple[str | None, int | None]:
    """Return (field, offset) where ``quote`` occurs verbatim, or (None, None)."""
    if not quote:
        return None, None
    for field_name in TEXT_FIELDS:
        text = str(row.get(field_name) or "")
        idx = text.find(quote)
        if idx >= 0:
            return field_name, idx
    return None, None


def select_span(
    row: dict,
    *,
    rules: Any,
    profile: dict,
    decide_label,
    max_candidates: int | None = None,
    guard: dict[str, Any] | None = None,
    precision_guard: bool = False,
    content_filter: bool = True,
) -> SpanSelection:
    """Pick the first verbatim span the frozen gate confirms, else abstain.

    The row's existing evidence is tried first, so a row that already carries a
    passing verbatim quote is unchanged.  Only when that fails is the bounded
    scan run.
    """
    status = _proposal_status(row)
    candidates = field_candidates(row)
    if max_candidates is not None:
        candidates = candidates[: int(max_candidates)]

    existing = str(row.get("counter_evidence") or "").strip()
    baseline_label = None
    baseline_reason = None
    baseline_defect = ""
    if existing:
        existing_field, existing_start = _locate_quote(existing, row)
        # Direction v67 P0: the deterministic content-quality filter runs on the
        # INCUMBENT quote BEFORE the frozen gate, so a letterhead that the gate
        # merely abstains on (accepted PATH_SCOPE_RESIDUAL pivot_absent) can no
        # longer keep the row's verified flag.  The filter only removes the span;
        # it never edits the gate, the rubric or a threshold.
        if content_filter:
            cf_ok, cf_reason = passes_content_filter(
                existing,
                row,
                start=existing_start if existing_start is not None else -1,
            )
            if not cf_ok:
                baseline_defect = cf_reason
                baseline_label = "ABSTAIN"
                baseline_reason = cf_reason
        if not baseline_defect:
            base_row = _minimal_row(row, status, existing)
            base_dec = decide_label(base_row, rules, profile)
            baseline_label = "ABSTAIN" if base_dec.abstained else base_dec.label
            baseline_reason = base_dec.reason_code
            if not base_dec.abstained:
                # Verify against whichever field actually carries it; scanning is
                # unnecessary if the incumbent quote is already verbatim AND (when
                # the guard is on) anchored to this query.
                for c in candidates:
                    if c.quote == existing or (
                        existing_field == c.field
                        and verify_span(str(row.get(c.field) or ""), existing, c.start, c.end)
                    ):
                        if precision_guard and not span_passes_precision_guard(existing, guard or {}):
                            baseline_reason = "off_topic_span"
                            break
                        return SpanSelection(
                            selected=True,
                            reason_code="supported_existing_span",
                            quote=existing,
                            field=c.field,
                            start=c.start,
                            end=c.end,
                            n_candidates=len(candidates),
                            n_evaluated=0,
                            decision=base_dec,
                            baseline_label=baseline_label,
                            baseline_reason=baseline_reason,
                            scanned_fields=[],
                            guard_available=bool((guard or {}).get("available", True)),
                            n_guard_rejected=0,
                        )
                # Existing quote passes the gate but is not a literal substring of
                # any named field -> do not claim verbatim; fall through to scan.
                baseline_reason = baseline_reason or "existing_not_verbatim"

    scanned: list[str] = []
    n_eval = 0
    n_guard_rejected = 0
    n_content_rejected = 0
    defect_reason = ""
    for cand in candidates:
        n_eval += 1
        if cand.field not in scanned:
            scanned.append(cand.field)
        # Deterministic content-quality filter (D2/D3/D4) runs BEFORE the gate;
        # a defective candidate is never offered to the frozen classifier.
        if content_filter:
            cf_ok, cf_reason = passes_content_filter(cand.quote, row, start=cand.start)
            if not cf_ok:
                n_content_rejected += 1
                if not defect_reason:
                    defect_reason = cf_reason
                if baseline_reason is None:
                    baseline_reason = cf_reason
                continue
        probe = _minimal_row(row, status, cand.quote)
        dec = decide_label(probe, rules, profile)
        if dec.abstained:
            if baseline_reason is None:
                baseline_reason = dec.reason_code
            continue
        # Byte-exact proof against the field the span came from.
        if not verify_span(str(row.get(cand.field) or ""), cand.quote, cand.start, cand.end):
            continue
        if precision_guard and not span_passes_precision_guard(cand.quote, guard or {}):
            n_guard_rejected += 1
            continue
        return SpanSelection(
            selected=True,
            reason_code="supported_verbatim_span",
            quote=cand.quote,
            field=cand.field,
            start=cand.start,
            end=cand.end,
            n_candidates=len(candidates),
            n_evaluated=n_eval,
            decision=dec,
            baseline_label=baseline_label,
            baseline_reason=baseline_reason,
            scanned_fields=scanned,
            guard_available=bool((guard or {}).get("available", True)),
            n_guard_rejected=n_guard_rejected,
            baseline_defect=baseline_defect,
            n_content_rejected=n_content_rejected,
        )

    if baseline_defect:
        reason_code = baseline_defect
    elif defect_reason:
        reason_code = defect_reason
    elif n_guard_rejected:
        reason_code = "off_topic_span"
    else:
        reason_code = baseline_reason or "no_emitting_span"
    return SpanSelection(
        selected=False,
        reason_code=reason_code,
        n_candidates=len(candidates),
        n_evaluated=n_eval,
        baseline_label=baseline_label,
        baseline_reason=baseline_reason,
        scanned_fields=scanned,
        guard_available=bool((guard or {}).get("available", True)),
        n_guard_rejected=n_guard_rejected,
        baseline_defect=baseline_defect,
        n_content_rejected=n_content_rejected,
    )


def _text_sha256(row: dict, field_name: str) -> str:
    return hashlib.sha256(str(row.get(field_name) or "").encode("utf-8")).hexdigest()


def _iter_candidates(decisions: Iterable[dict]) -> Iterable[dict]:
    for d in decisions:
        status = str(d.get("counter_status") or "")
        if status in SCORED_STATUSES:
            yield d
            continue
        if d.get("adversarial_retrieval_signal") or d.get("adversarial_intent"):
            yield d


def apply_verified_span_selection(
    bundle: dict,
    *,
    qid: str | None = None,
    mode: str | None = None,
    env: dict[str, str] | None = None,
) -> dict:
    """Select and verify counter-evidence spans before the accepted anchor gate.

    Writes only the counter fields the accepted path already owns
    (``counter_status`` / ``counter_evidence`` / ``counter_uncertainty``) plus
    this seam's own ``counter_evidence_span`` audit record.  Geometry, ranks,
    clusters and relations are untouched.
    """
    out = copy.deepcopy(bundle)
    chosen = mode or _mode(env)
    prov_base = {
        "version": SPAN_VERSION,
        "mode": chosen,
        "text_fields": list(TEXT_FIELDS),
        "min_span_chars": MIN_SPAN_CHARS,
        "max_candidates_per_field": MAX_CANDIDATES_PER_FIELD,
        "selection_order": "row_status_then_field_then_text_order",
        "claim_ceiling": (
            "The span is verified verbatim and the frozen classifier confirms or "
            "abstains. This seam never asserts that a decision IS supporting, "
            "contrary or limiting; emitted labels remain the row's own proposal."
        ),
    }
    if chosen != MODE_SELECT:
        out.setdefault("provenance", {})["counter_evidence_span"] = {
            **prov_base, "applied": False, "reason": "selection disabled",
        }
        return out

    query = str(out.get("query") or "")
    try:
        rules, digest = load_frozen_rules()
    except Exception as exc:  # noqa: BLE001 - fail safe, never silently re-score
        out.setdefault("provenance", {})["counter_evidence_span"] = {
            **prov_base,
            "applied": False,
            "reason": f"frozen_rules_unavailable: {exc.__class__.__name__}",
        }
        return out
    profile = resolve_anchor_profile(rules, qid=qid, query=query)
    if profile is None:
        out.setdefault("provenance", {})["counter_evidence_span"] = {
            **prov_base,
            "applied": False,
            "reason": "no_frozen_anchor_profile_for_query",
            "frozen_rules_sha256": digest,
        }
        return out
    decide_label, _load = _import_component()
    env_map = env if env is not None else os.environ
    precision_guard = str(env_map.get(SPAN_GUARD_ENV, "on")).strip().lower() not in (
        "off", "0", "false", "no",
    )
    guard = guard_terms(profile, query)

    n_candidates = 0
    n_selected = 0
    n_abstained = 0
    n_evaluated = 0
    n_guard_rejected = 0
    n_content_rejected = 0
    n_baseline_cleared = 0
    baseline_cleared_ids: list[str] = []
    selected_ids: list[str] = []
    abstained_ids: list[str] = []
    reasons: dict[str, int] = {}
    for d in _iter_candidates(out.get("decisions") or []):
        n_candidates += 1
        sel = select_span(
            d,
            rules=rules,
            profile=profile,
            decide_label=decide_label,
            guard=guard,
            precision_guard=precision_guard,
        )
        n_evaluated += sel.n_evaluated
        n_guard_rejected += sel.n_guard_rejected
        n_content_rejected += sel.n_content_rejected
        record = sel.to_dict()
        if sel.field:
            record["field_sha256"] = _text_sha256(d, sel.field)
        d["counter_evidence_span"] = record
        if not sel.selected:
            n_abstained += 1
            abstained_ids.append(str(d.get("decision_id") or ""))
            reasons[sel.reason_code] = reasons.get(sel.reason_code, 0) + 1
            # Direction v67 P0: if the incumbent evidence was content-defective
            # (letterhead / markup / language mismatch), revoke the verified
            # claim even when the frozen gate abstains.  Otherwise a
            # "pivot_absent" row would keep serving its letterhead as sourced
            # counter-authority.
            if sel.baseline_defect:
                d["counter_evidence"] = ""
                d["counter_evidence_verified"] = False
                d["counter_evidence_quality_filter"] = {
                    "version": "counter_content_quality/1",
                    "rejected": True,
                    "reason_code": sel.baseline_defect,
                    "span_reason_code": sel.reason_code,
                }
                n_baseline_cleared += 1
                baseline_cleared_ids.append(str(d.get("decision_id") or ""))
            continue
        n_selected += 1
        selected_ids.append(str(d.get("decision_id") or ""))
        # Keep the row's own proposal; the frozen gate confirms it.
        d["counter_status"] = _proposal_status(d)
        d["counter_evidence"] = sel.quote
        d["counter_evidence_verified"] = True
        if sel.decision is not None:
            d["counter_uncertainty"] = sel.decision.uncertainty
        d["counter_proposal_source"] = SPAN_VERSION

    out.setdefault("provenance", {})["counter_evidence_span"] = {
        **prov_base,
        "applied": True,
        "frozen_rules_sha256": digest,
        "qid": qid,
        "anchor_profile": next(
            (k for k, v in (getattr(rules, "anchors", {}) or {}).items() if v is profile),
            None,
        ),
        "n_candidates": n_candidates,
        "n_selected": n_selected,
        "n_abstained": n_abstained,
        "n_sentences_evaluated": n_evaluated,
        "precision_guard": precision_guard,
        "guard_available": bool(guard.get("available")),
        "guard_statutes": list(guard.get("statutes") or []),
        "guard_phrase_count": len(guard.get("phrases") or []),
        "n_guard_rejected": n_guard_rejected,
        "n_content_rejected": n_content_rejected,
        "n_baseline_cleared": n_baseline_cleared,
        "baseline_cleared_ids": baseline_cleared_ids,
        "selected_ids": selected_ids,
        "abstained_ids": abstained_ids,
        "abstention_reasons": dict(sorted(reasons.items())),
    }
    return out


__all__ = [
    "SPAN_ENV",
    "SPAN_GUARD_ENV",
    "SPAN_VERSION",
    "guard_terms",
    "span_passes_precision_guard",
    "SpanCandidate",
    "SpanSelection",
    "apply_verified_span_selection",
    "field_candidates",
    "select_span",
    "sentence_spans",
    "verify_span",
]

# ---- Content quality filter (direction v66 P0) ----
# Deterministic, model-free filter to catch D2/D3/D4 defects.
# Filter only narrows which spans are offered; never touches decide_label.

import unicodedata

COURT_HEADER_MARKERS = (
    "bundesgericht",
    "tribunal fédéral",
    "tribunale federale",
    "obergericht",
    "kantonsgericht",
    "verwaltungsgericht",
    "handelsgericht",
    "sozialversicherungsgericht",
    "bezirksgericht",
    "kreisgericht",
    "landgericht",
    "appellationsgericht",
    "cour de justice",
    "tribunal cantonal",
    "tribunale cantonale",
    "dretgira",
    "gericht",
)

#: Frozen D2 offset ceiling (mirrors evaluation/counter_evidence_quality_benchmark.py).
LETTERHEAD_ZONE_OFFSET_MAX = 400

#: Lines whose *start* marks a judgment head / letterhead rather than prose.
HEADER_LINE_PATTERNS = [
    re.compile(r'(?i)^\s*(bundesgericht|tribunal\s+f[ée]d[ée]ral|tribunale\s+federale|kantonsgericht|obergericht|appellationsgericht|bezirksgericht|kreisgericht|landgericht|verwaltungsgericht|handelsgericht|sozialversicherungsgericht|cour\s+de\s+justice|tribunal\s+cantonal|tribunale\s+cantonale|dretgira)\b'),
    re.compile(r'(?i)^\s*(urteilskopf|auszug\s+aus\s+dem\s+urteil|extrait\s+de\s+l.?arr[êe]t|estratto\s+della\s+sentenza)\b'),
    re.compile(r'(?i)^\s*(urteil|arr[êe]t|sentenza|beschluss|verf[üu]gung|entscheid)\s+(vom|du|del|della)\b'),
    re.compile(r'(?i)^\s*(gesch[äa]fts-?\s*nr\.?|gesch[äa]ftsnummer|num[ée]ro\s+de\s+dossier|n\.\s*rif\.?|ref\.?:|schriftlich\s+mitgeteilt|mitgeteilt\s+am)\b'),
]

#: A bare case-number line ("110 II 391", "5A_123/2020", "B 1/2021").
CASE_NUMBER_RE = re.compile(r'^\s*([A-Z]?\s?\d{1,4}\s*(?:[IVX]{1,4}\s*)?\d{1,5}(?:/\d{2,4})?|\d{1,4}\s+[IVX]{1,4}\s+\d{1,5})\s*$')

MARKUP_RESIDUE_PATTERNS = [
    re.compile(r'<[^>]+>'),  # HTML tags
    re.compile(r'\[\[.*?\]\]'),  # wiki markup
    re.compile(r'\{\{.*?\}\}'),  # template markup
    re.compile(r'&[a-zA-Z]+;'),  # HTML entities
    re.compile(r'\\[a-zA-Z]+\{'),  # LaTeX-ish
]

# Frozen D4 marker sets (mirrors evaluation/counter_evidence_quality_benchmark.py).
LANGUAGE_MARKER_SETS = {
    "de": ("Regeste", "Erwägung", "Kündigung", "Mietvertrag", "Bundesgericht", "Verfügung"),
    "fr": ("considérant", "bail", "résiliation", "recours", "Tribunal fédéral", "arrêt"),
    "it": ("considerando", "locazione", "disdetta", "ricorso", "Tribunale federale", "sentenza"),
}


def _normalize_text(s: str) -> str:
    if not s:
        return ""
    # strip diacritics for comparison
    s2 = unicodedata.normalize("NFKD", str(s))
    s2 = "".join(c for c in s2 if not unicodedata.combining(c))
    return s2.lower()


def _header_line_score(line: str) -> int:
    stripped = line.strip()
    if not stripped:
        return 0
    for pat in HEADER_LINE_PATTERNS:
        if pat.search(stripped):
            return 2
    norm = _normalize_text(stripped)
    if any(marker in norm for marker in COURT_HEADER_MARKERS) and len(stripped) <= 90:
        return 1
    if CASE_NUMBER_RE.match(stripped):
        return 1
    if re.match(r'^[_\-\s]{4,}$', stripped):
        return 1
    return 0


def looks_like_header_span(quote: str, full_text: str, start: int = -1) -> bool:
    """True iff ``quote`` is a judgment letterhead / head block (D2).

    Constrained to the frozen D2 zone (offset < 400) and to *header-shaped*
    lines, so a substantive sentence that merely sits near the document start is
    not rejected.
    """
    if not quote:
        return False
    offset = start
    if offset is None or offset < 0:
        offset = (full_text or "").find(quote)
    if offset is None or offset < 0 or offset >= LETTERHEAD_ZONE_OFFSET_MAX:
        return False
    lines = [ln.strip() for ln in str(quote).splitlines() if ln.strip()]
    if not lines:
        return False
    head = lines[:6]
    first_two = head[:2]
    # A strong header line among the first two lines is sufficient.
    if any(_header_line_score(ln) == 2 for ln in first_two):
        return True
    # Two or more header-ish fields in the head block (court name + case number,
    # `Urteilskopf` + docket, etc.).
    score = sum(1 for ln in head if _header_line_score(ln))
    if score >= 2:
        return True
    # Case number followed by a judgment-head phrase.
    if len(head) >= 2 and CASE_NUMBER_RE.match(head[0]):
        if re.search(r'(?i)(urteil|arr[êe]t|sentenza|auszug|extrait|estratto)', head[1]):
            return True
    return False


def detect_letterhead_zone(text: str, start: int = 0, max_check_chars: int = 500) -> bool:
    """Backwards-compatible D2 helper: inspect the head run of ``text``."""
    if not text:
        return False
    if start is None:
        start = 0
    if start > LETTERHEAD_ZONE_OFFSET_MAX:
        return False
    head = str(text)[:max_check_chars]
    return looks_like_header_span(head, str(text), 0)


def detect_markup_residue(text: str) -> bool:
    """Detect D3: markup residue."""
    if not text:
        return False
    for pat in MARKUP_RESIDUE_PATTERNS:
        if pat.search(text):
            return True
    # Also check for leftover tags like <p>, </div> etc
    if re.search(r'</?[a-z][^>]{0,20}>', text):
        return True
    return False


def detect_language_marker_mismatch(quote: str, row_lang: str) -> bool:
    """Detect D4: row language has no marker while another language has >=3."""
    if not quote or not row_lang:
        return False
    row_lang = str(row_lang).lower()[:2]
    if row_lang not in LANGUAGE_MARKER_SETS:
        return False

    def hits(lang: str) -> int:
        return sum(1 for marker in LANGUAGE_MARKER_SETS[lang] if marker in quote)

    own = hits(row_lang)
    best_other = max((hits(lang), lang) for lang in LANGUAGE_MARKER_SETS if lang != row_lang)
    return own == 0 and best_other[0] >= 3


def passes_content_filter(quote: str, row: dict, start: int = -1) -> tuple[bool, str]:
    """Returns (passes, reason_if_failed). Deterministic; model-free."""
    # D2: letterhead / judgment-head zone
    full_text = str(row.get('full_text') or '')
    if looks_like_header_span(quote, full_text, start=start):
        return False, 'd2_letterhead_zone'

    # D3: markup residue
    if detect_markup_residue(quote):
        return False, 'd3_markup_residue'

    # D4: language marker mismatch
    row_lang = row.get('language') or row.get('lang')
    if detect_language_marker_mismatch(quote, row_lang):
        return False, 'd4_language_marker_mismatch'

    return True, ''

