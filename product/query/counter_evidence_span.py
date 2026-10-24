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
    content_filter_rejections: dict[str, int] = dc_field(default_factory=dict)

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
            "content_filter_rejections": dict(self.content_filter_rejections),
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
    if existing:
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
                    c.field and verify_span(str(row.get(c.field) or ""), existing, c.start, c.end)
                ):
                    if precision_guard and not span_passes_precision_guard(existing, guard or {}):
                        baseline_reason = "off_topic_span"
                        break
                    # Content quality filter (D2/D3/D4)
                    if content_filter:
                        cf_ok, cf_reason = passes_content_filter(existing, row, start=c.start)
                        if not cf_ok:
                            return SpanSelection(
                                selected=False,
                                reason_code=cf_reason,
                                quote="",
                                field="",
                                start=-1,
                                end=-1,
                                n_candidates=len(candidates),
                                n_evaluated=0,
                                decision=base_dec,
                                baseline_label=baseline_label,
                                baseline_reason=cf_reason,
                                scanned_fields=[],
                                guard_available=bool((guard or {}).get("available", True)),
                                n_guard_rejected=0,
                            )
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
    content_filter_rejections: dict[str, int] = {}
    for cand in candidates:
        n_eval += 1
        if cand.field not in scanned:
            scanned.append(cand.field)
        # Byte-exact proof against the field the span came from.
        if not verify_span(str(row.get(cand.field) or ""), cand.quote, cand.start, cand.end):
            continue
        # Content quality filter (D2/D3/D4) - runs before frozen gate to narrow spans offered
        if content_filter:
            cf_ok, cf_reason = passes_content_filter(cand.quote, row, start=cand.start)
            if not cf_ok:
                content_filter_rejections[cf_reason] = content_filter_rejections.get(cf_reason, 0) + 1
                continue
        if precision_guard and not span_passes_precision_guard(cand.quote, guard or {}):
            n_guard_rejected += 1
            continue
        probe = _minimal_row(row, status, cand.quote)
        dec = decide_label(probe, rules, profile)
        if dec.abstained:
            if baseline_reason is None:
                baseline_reason = dec.reason_code
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
            content_filter_rejections=content_filter_rejections,
        )

    # Determine the primary content filter rejection reason (most frequent)
    cf_primary = ""
    if content_filter_rejections:
        cf_primary = max(content_filter_rejections.items(), key=lambda x: x[1])[0]

    return SpanSelection(
        selected=False,
        reason_code=(
            cf_primary if cf_primary
            else ("off_topic_span" if n_guard_rejected
                 else (baseline_reason or "no_emitting_span"))
        ),
        n_candidates=len(candidates),
        n_evaluated=n_eval,
        baseline_label=baseline_label,
        baseline_reason=baseline_reason,
        scanned_fields=scanned,
        guard_available=bool((guard or {}).get("available", True)),
        n_guard_rejected=n_guard_rejected,
        content_filter_rejections=content_filter_rejections,
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
        record = sel.to_dict()
        if sel.field:
            record["field_sha256"] = _text_sha256(d, sel.field)
        d["counter_evidence_span"] = record
        if not sel.selected:
            n_abstained += 1
            abstained_ids.append(str(d.get("decision_id") or ""))
            reasons[sel.reason_code] = reasons.get(sel.reason_code, 0) + 1
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

    # Aggregate content filter rejections across all rows
    cf_histogram: dict[str, int] = {}
    for d in out.get("decisions") or []:
        span_rec = d.get("counter_evidence_span") or {}
        for k, v in (span_rec.get("content_filter_rejections") or {}).items():
            cf_histogram[k] = cf_histogram.get(k, 0) + v

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
        "content_filter_rejections": dict(sorted(cf_histogram.items())),
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
    "cour de justice",
    "tribunal cantonal",
)

COURT_HEADER_PATTERNS = [
    re.compile(r'(?i)^\s*(bundesgericht|tribunal\s+f[ée]d[ée]ral|tribunale\s+federale)\s*$', re.M),
    re.compile(r'(?i)^(bundesverwaltungsgericht|tribunal\s+administratif\s+f[ée]d[ée]ral|tribunale\s+amministrativo\s+federale)\s*$', re.M),
    re.compile(r'(?i)^.*(Geschäfts-?\s*Nr\.|Numéro\s+de\s+dossier|N\.\s*rif\.|Règlement|arrêt\s+du|Urteil\s+vom|sentenza\s+del).*(\d{4}|[A-Z])', re.M),
]

MARKUP_RESIDUE_PATTERNS = [
    re.compile(r'<[^>]+>'),  # HTML tags
    re.compile(r'\[\[.*?\]\]'),  # wiki markup
    re.compile(r'\{\{.*?\}\}'),  # template markup
    re.compile(r'&[a-zA-Z]+;'),  # HTML entities
    re.compile(r'\\[a-zA-Z]+\{'),  # LaTeX-ish
]

def _normalize_text(s: str) -> str:
    if not s:
        return ""
    # strip diacritics for comparison
    s2 = unicodedata.normalize("NFKD", str(s))
    s2 = "".join(c for c in s2 if not unicodedata.combining(c))
    return s2.lower()


def detect_letterhead_zone(text: str, start: int = 0, max_check_chars: int = 500) -> bool:
    """Detect D2: evidence_head starting at full_text offset 0 with court-header text."""
    if not text:
        return False
    # Check if start is near beginning (evidence head at offset ~0)
    if start > 50:  # allow small offset
        return False
    check = text[:max_check_chars]
    norm = _normalize_text(check)
    # Look for court header patterns
    header_lines = check.split('\n')[:10]  # first few lines
    for i, line in enumerate(header_lines[:6]):  # check first 6 lines
        line_norm = _normalize_text(line)
        if not line_norm.strip():
            continue
        # Court name markers
        for marker in COURT_HEADER_MARKERS:
            if marker in line_norm:
                # Likely letterhead if it's in early lines
                if i <= 4:
                    return True
        # Date/case number patterns typical of headers
        if re.search(r'(?i)^(urteil|arrêt|sentenza|beschluss)\s+(vom|du|del)', line_norm):
            if i <= 3:
                return True
        # Lots of caps and short header-like content
        if re.match(r'^[A-ZÄÖÜÉÈÊÀÂÆÇÎÏÔŒÙÛË\s\.\-0-9]+$', line.strip()) and len(line.strip()) < 80 and i <= 2:
            if any(c.isdigit() for c in line) or any(m in line_norm for m in COURT_HEADER_MARKERS):
                return True
    return False


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
    """Detect D4: language marker mismatch between row language and span text."""
    if not quote or not row_lang:
        return False
    row_lang = str(row_lang).lower()[:2]
    norm = _normalize_text(quote)
    # Simple heuristics: check for obvious wrong language markers
    de_markers = set(['der', 'die', 'das', 'und', 'ist', 'sind', 'wird', 'werden', 'nicht', 'oder'])
    fr_markers = set(['le', 'la', 'les', 'et', 'est', 'sont', 'ne', 'pas', 'ou', 'dans'])
    it_markers = set(['il', 'lo', 'la', 'gli', 'le', 'e', 'sono', 'non', 'o', 'nel'])
    
    words = set(norm.split())
    de_score = len(words & de_markers)
    fr_score = len(words & fr_markers)
    it_score = len(words & it_markers)
    
    scores = {'de': de_score, 'fr': fr_score, 'it': it_score}
    best = max(scores.items(), key=lambda x: x[1])[0]
    if best and best != row_lang and max(scores.values()) >= 3 and scores[best] > scores.get(row_lang, 0) * 2:
        return True
    return False


def passes_content_filter(quote: str, row: dict, start: int = 0) -> tuple[bool, str]:
    """Returns (passes, reason_if_failed)."""
    # D2: letterhead zone
    full_text = str(row.get('full_text') or '')
    if detect_letterhead_zone(full_text, start=start):
        return False, 'd2_letterhead_zone'
    # Check if quote comes from early in full_text
    if full_text and quote and quote in full_text:
        idx = full_text.find(quote)
        if idx >= 0 and detect_letterhead_zone(full_text, start=idx):
            return False, 'd2_letterhead_zone'
    
    # D3: markup residue
    if detect_markup_residue(quote):
        return False, 'd3_markup_residue'
    if detect_markup_residue(full_text[:start+len(quote)+100] if start >=0 else quote):
        # be more specific
        pass
    
    # D4: language marker mismatch
    row_lang = row.get('language') or row.get('lang')
    if detect_language_marker_mismatch(quote, row_lang):
        return False, 'd4_language_marker_mismatch'
    
    return True, ''
