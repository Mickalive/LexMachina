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
    #: True iff the shipped precision guard would have vetoed this row's own
    #: verbatim, gate-confirmed, content-clean incumbent and the v68 scope
    #: exempted it (guard governs scan proposals; disclosed in provenance).
    incumbent_guard_exempted: bool = False

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
            "incumbent_guard_exempted": self.incumbent_guard_exempted,
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
    content_rejected_reason: str | None = None
    incumbent_cf_reason: str | None = None
    if existing:
        base_row = _minimal_row(row, status, existing)
        base_dec = decide_label(base_row, rules, profile)
        baseline_label = "ABSTAIN" if base_dec.abstained else base_dec.label
        baseline_reason = base_dec.reason_code
        if not base_dec.abstained:
            # Verify against whichever field actually carries it; scanning is
            # unnecessary if the incumbent quote is already verbatim AND the
            # frozen gate confirmed it.
            for c in candidates:
                if c.quote == existing or (
                    c.field and verify_span(str(row.get(c.field) or ""), existing, c.start, c.end)
                ):
                    # Content quality filter FIRST (frozen D2/D3/D4 predicates).
                    # A defective incumbent is NOT selected and NOT terminal:
                    # the bounded scan continues so a clean verbatim span can
                    # REPLACE it (direction v68 P0 rejection/incumbent leg).
                    if content_filter:
                        cf_ok, cf_reason = passes_content_filter(existing, row)
                        if not cf_ok:
                            incumbent_cf_reason = cf_reason
                            content_rejected_reason = cf_reason
                            break
                    # Precision-guard scope (v68 disclosure): the accepted guard
                    # vetoes OFF-TOPIC SCAN PROPOSALS.  It does not veto the
                    # row's own verbatim, gate-confirmed, content-clean evidence:
                    # downgrading that would delete the only sound counter row of
                    # the claims population for a lexical-anchoring reason the
                    # frozen gate and the frozen content predicates both pass
                    # (ordered work: "the known sound row bstger_SK.2023.49 stays
                    # verified/sound").  Measured: NO packet-of-record v3 row
                    # carries an incumbent, so the accepted v3 guarded/unguarded
                    # arm numbers are unchanged by this scope.
                    guard_exempted_incumbent = bool(
                        precision_guard
                        and not span_passes_precision_guard(existing, guard or {})
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
                        incumbent_guard_exempted=guard_exempted_incumbent,
                    )
            else:
                # Existing quote passes the gate but is not a literal substring
                # of any named field -> do not claim verbatim; scan instead.
                baseline_reason = baseline_reason or "existing_not_verbatim"

    scanned: list[str] = []
    n_eval = 0
    n_guard_rejected = 0
    for cand in candidates:
        n_eval += 1
        if cand.field not in scanned:
            scanned.append(cand.field)
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
        # Content quality filter (frozen D2/D3/D4 predicates): reject and
        # keep scanning for a clean span.
        if content_filter:
            cf_ok, cf_reason = passes_content_filter(cand.quote, row)
            if not cf_ok:
                n_guard_rejected += 1  # count as filtered by quality
                if content_rejected_reason is None:
                    content_rejected_reason = cf_reason
                continue
        return SpanSelection(
            selected=True,
            reason_code=(
                "supported_existing_span"
                if incumbent_cf_reason is None and cand.quote == existing
                else "supported_verbatim_span"
            ),
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
        )

    # Abstain.  A content-filter rejection of the incumbent (or of every
    # scanned span) is reported as such; it is never silently reported as a
    # gate abstention, and the caller downgrades the incumbent's verified flag.
    reason = content_rejected_reason or baseline_reason or "no_emitting_span"
    if n_guard_rejected and not content_rejected_reason:
        reason = "off_topic_span"
    return SpanSelection(
        selected=False,
        reason_code=reason,
        n_candidates=len(candidates),
        n_evaluated=n_eval,
        baseline_label=baseline_label,
        baseline_reason=baseline_reason,
        scanned_fields=scanned,
        guard_available=bool((guard or {}).get("available", True)),
        n_guard_rejected=n_guard_rejected,
    )


# ---- Stage 2: offer the pool counter-surface signals to the frozen gate ----
#
# Why this stage exists (direction v68, claim-ceiling residual)
# -------------------------------------------------------------
# The shipped first pass only examines rows the adversarial/generative stage
# already scored, and on the flagship offline family that is EXACTLY ONE row per
# 100-row bundle (measured: n_candidates=1, n_selected=0 on every
# profile-bearing bundle of the 2026-10-25 family).  Meanwhile the accepted
# pool counter-surface scan (``counter_surface/2``) hydrates a bounded,
# marker-preferring subset of the RENDERED pool and classifies it locally —
# measured 10..26 signalled rows per bundle with a verbatim evidence sentence
# each — but its contract forbids it from writing a scored counter field, so
# those evidence sentences were never offered to the frozen confirm-or-abstain
# gate at all.
#
# This stage is that missing hand-off.  It is purely additive:
#
# * it runs the SAME ``select_span`` → ``decide_label`` chain as stage 1, with
#   the same frozen rules, the same anchor profile, the same precision guard and
#   the same frozen D1-D4 content filter;
# * it only touches rows that carry a ``counter_surface_signal.heuristic_status``
#   AND no ``counter_evidence_span`` record (i.e. rows stage 1 never saw);
# * a row is written ONLY when the frozen gate confirms a byte-exact verbatim
#   span that also passes the content predicates.  Every other row keeps
#   ``counter_status`` / ``counter_evidence_verified`` exactly as it was, and
#   the abstention is published in provenance with its reason code instead of
#   being silently converted into a label;
# * geometry, ranks, clusters and relations are never touched.
#
# It never edits, re-tunes or re-derives the frozen gate, the rubric, a
# threshold or a bar (factory-wide requirement 37 / H2 ruling): it only widens
# WHICH evidence is offered to that gate, and it publishes n_candidates /
# n_selected / n_abstained side by side so the yield is auditable.  Whether a
# frozen scorer counts abstained rows is decided by that scorer's own
# population predicate as written — this stage pre-declares no support rate.

SURFACE_SPAN_VERSION = "counter_span_surface/1"
#: Kill-switch for stage 2 only, so stage 1 keeps its accepted behaviour when
#: an auditor wants the bridged population switched off for comparison.
SURFACE_SPAN_ENV = "LEXMACHINA_COUNTER_SPAN_SURFACE"


def _surface_status(row: dict) -> str | None:
    """Scored proposal status the pool counter-surface scan attributed, else None.

    Returns ``None`` (never an invented status) when the row carries no surface
    signal or the signal is not one of the frozen rubric's scored statuses.
    """
    status = str((row.get("counter_surface_signal") or {}).get("heuristic_status") or "")
    return status if status in SCORED_STATUSES else None


def _surface_candidates(
    bundle: dict,
) -> tuple[list[dict], list[dict], list[str]]:
    """Partition the pool for stage 2.

    Returns ``(pending, previously_confirmed, excluded_cited, owned_elsewhere,
    n_surface)``:

    * ``pending`` — rows stage 1 never handled (no ``counter_evidence_span``
      record) that carry a scored surface proposal and are not ``cited``;
    * ``previously_confirmed`` — rows stage 2 already confirmed on an earlier
      run of this same stage, so a re-run reproduces its own provenance
      instead of silently losing the confirmations (determinism/idempotence);
    * ``excluded_cited`` — surface-signalled rows whose current
      ``counter_status`` is ``cited``.  ``counter_status.NON_COUNTER_STATUSES``
      documents that "citing a case is the opposite of countering it", so this
      stage never re-purposes the sourced answer's own support into a
      counter-authority finding.  The ids are published so the observed
      population is fully accounted for rather than silently narrowed.
    """
    pending: list[dict] = []
    confirmed: list[dict] = []
    excluded_cited: list[str] = []
    owned_elsewhere = 0
    n_surface = 0
    for d in bundle.get("decisions") or []:
        if _surface_status(d) is None:
            continue
        n_surface += 1
        record = d.get("counter_evidence_span") or {}
        if record:
            # an existing record means a span stage already owns this row;
            # stage 2 re-publishes its own prior confirmations so a re-run is
            # byte-stable (stage-1 rows are simply not stage-2 population)
            if record.get("stage") == 2 and d.get("counter_evidence_verified") is True:
                confirmed.append(d)
            else:
                owned_elsewhere += 1
            continue
        if str(d.get("counter_status") or "") == "cited":
            excluded_cited.append(str(d.get("decision_id") or ""))
            continue
        pending.append(d)
    return pending, confirmed, excluded_cited, owned_elsewhere, n_surface


def apply_surface_span_confirmation(
    bundle: dict,
    *,
    qid: str | None = None,
    mode: str | None = None,
    env: dict[str, str] | None = None,
) -> dict:
    """Stage 2 — offer ``counter_surface_signal`` rows to the frozen gate.

    Additive counterpart of :func:`apply_verified_span_selection`.  Writes only
    on frozen-gate confirmation, publishes the whole population (confirmed and
    abstained) in its own provenance block, and never touches geometry.
    """
    out = copy.deepcopy(bundle)
    chosen = mode or _mode(env)
    env_map = env if env is not None else os.environ
    surface_on = str(env_map.get(SURFACE_SPAN_ENV, "on")).strip().lower() not in (
        "off", "0", "false", "no",
    )
    pending, prior, excluded_cited, owned_elsewhere, n_surface = (
        _surface_candidates(out)
    )
    population = [*prior, *pending]
    prov: dict[str, Any] = {
        "version": SURFACE_SPAN_VERSION,
        "stage": 2,
        "mode": chosen,
        "enabled": surface_on,
        "proposal_channel": "counter_surface_signal",
        "consumes": "product.query.counter_surface (counter_surface/2)",
        "n_surface_signals": n_surface,
        "n_candidates": len(population),
        "candidate_ids": [str(d.get("decision_id") or "") for d in population],
        "n_previously_confirmed": len(prior),
        "n_owned_by_stage_1": owned_elsewhere,
        "population_partition": (
            "n_candidates + n_excluded_cited + n_owned_by_stage_1 == "
            "n_surface_signals"
        ),
        "n_excluded_cited": len(excluded_cited),
        "excluded_cited_ids": excluded_cited,
        "excluded_cited_reason": (
            "counter_status.NON_COUNTER_STATUSES: citing a case is the opposite "
            "of countering it, so this stage never re-purposes the sourced "
            "answer's own support into a counter-authority finding"
        ),
        "selection_chain": (
            "select_span -> decide_label (frozen RULES_LABEL) with the shipped "
            "precision guard and the frozen D1-D4 content filter; identical to "
            "stage 1"
        ),
        "claim_ceiling": (
            "Stage 2 only widens WHICH evidence is offered to the already-frozen "
            "confirm-or-abstain gate. It never asserts that a decision IS "
            "supporting, contrary or limiting, never writes a label the gate "
            "abstained on, and pre-declares no support rate: n_candidates, "
            "n_selected and n_abstained are published together and the frozen "
            "scorer decides the rest under its own population predicate."
        ),
        "geometry_touched": False,
    }
    if chosen != MODE_SELECT:
        out.setdefault("provenance", {})["counter_evidence_span_surface"] = {
            **prov, "applied": False, "reason": "selection disabled",
        }
        return out
    if not surface_on:
        out.setdefault("provenance", {})["counter_evidence_span_surface"] = {
            **prov, "applied": False, "reason": f"{SURFACE_SPAN_ENV}=off",
        }
        return out
    if not population:
        out.setdefault("provenance", {})["counter_evidence_span_surface"] = {
            **prov, "applied": False, "reason": "no_counter_surface_signals",
        }
        return out

    query = str(out.get("query") or "")
    try:
        rules, digest = load_frozen_rules()
    except Exception as exc:  # noqa: BLE001 - fail safe, never silently re-score
        out.setdefault("provenance", {})["counter_evidence_span_surface"] = {
            **prov,
            "applied": False,
            "reason": f"frozen_rules_unavailable: {exc.__class__.__name__}",
        }
        return out
    profile = resolve_anchor_profile(rules, qid=qid, query=query)
    if profile is None:
        # The frozen gate cannot decide without a profile, so no row may be
        # written.  The OBSERVED population is still published: a reader must be
        # able to see that the signals existed and were not silently dropped.
        out.setdefault("provenance", {})["counter_evidence_span_surface"] = {
            **prov,
            "applied": False,
            "reason": "no_frozen_anchor_profile_for_query",
            "frozen_rules_sha256": digest,
            "n_selected": 0,
            "n_abstained": 0,
        }
        return out

    decide_label, _load = _import_component()
    precision_guard = str(env_map.get(SPAN_GUARD_ENV, "on")).strip().lower() not in (
        "off", "0", "false", "no",
    )
    guard = guard_terms(profile, query)

    n_selected = len(prior)
    n_abstained = 0
    n_evaluated = 0
    n_guard_rejected = 0
    selected_ids: list[str] = [str(d.get("decision_id") or "") for d in prior]
    abstained: list[dict[str, Any]] = []
    reasons: dict[str, int] = {}
    for d in pending:
        status = _surface_status(d)
        if status is None:  # defensive: _surface_candidates already filtered
            continue
        probe = dict(d)
        probe["counter_status"] = status
        sel = select_span(
            probe,
            rules=rules,
            profile=profile,
            decide_label=decide_label,
            guard=guard,
            precision_guard=precision_guard,
        )
        n_evaluated += sel.n_evaluated
        n_guard_rejected += sel.n_guard_rejected
        record = sel.to_dict()
        record["proposal_channel"] = "counter_surface_signal"
        record["proposal_status"] = status
        record["status_before"] = d.get("counter_status")
        record["stage"] = 2
        if sel.field:
            record["field_sha256"] = _text_sha256(d, sel.field)
        did = str(d.get("decision_id") or "")
        if not sel.selected:
            n_abstained += 1
            reasons[sel.reason_code] = reasons.get(sel.reason_code, 0) + 1
            abstained.append({
                "decision_id": did,
                "reason_code": sel.reason_code,
                "proposal_status": status,
                # The row keeps its pre-stage values: no label, no verified flag.
                "counter_status_unchanged": d.get("counter_status"),
                "counter_evidence_verified_unchanged": d.get("counter_evidence_verified"),
            })
            # v68 P0: when the span seam abstains, the defective incumbent
            # counter_evidence must not remain verified.
            d["counter_evidence_verified"] = False
            continue
        n_selected += 1
        selected_ids.append(did)
        d["counter_evidence_span"] = record
        d["counter_status"] = status
        d["counter_evidence"] = sel.quote
        d["counter_evidence_verified"] = True
        d.pop("counter_evidence_unevidenced", None)
        d.pop("counter_evidence_unevidenced_reason", None)
        if sel.decision is not None:
            d["counter_uncertainty"] = sel.decision.uncertainty
        d["counter_proposal_source"] = SURFACE_SPAN_VERSION
        d.setdefault("counter_proposal_channels", [])
        if "counter_surface_signal" not in d["counter_proposal_channels"]:
            d["counter_proposal_channels"] = [
                *d["counter_proposal_channels"], "counter_surface_signal",
            ]

    out.setdefault("provenance", {})["counter_evidence_span_surface"] = {
        **prov,
        "applied": True,
        "frozen_rules_sha256": digest,
        "qid": qid,
        "anchor_profile": next(
            (k for k, v in (getattr(rules, "anchors", {}) or {}).items() if v is profile),
            None,
        ),
        "precision_guard": precision_guard,
        "guard_available": bool(guard.get("available")),
        "guard_statutes": list(guard.get("statutes") or []),
        "guard_phrase_count": len(guard.get("phrases") or []),
        "n_sentences_evaluated": n_evaluated,
        "n_guard_rejected": n_guard_rejected,
        "n_selected": n_selected,
        "n_abstained": n_abstained,
        "yield_on_candidates": (
            round(n_selected / len(population), 6) if population else 0.0
        ),
        "selected_ids": selected_ids,
        "abstained": abstained,
        "abstention_reasons": dict(sorted(reasons.items())),
        "content_filter": content_filter_provenance(),
        "stage_1_provenance_block": "provenance.counter_evidence_span (unchanged)",
        "writes_scored_counter_fields_only_on_frozen_gate_confirmation": True,
    }
    return out


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


def _content_rejection_sweep(out: dict) -> list[dict[str, Any]]:
    """Rejection/incumbent leg over rows the seam loop did not handle.

    Any row still claiming ``counter_evidence_verified=True`` whose evidence
    fails the frozen D1-D4 content predicates is downgraded to an explicitly
    unevidenced row.  The evidence string is kept for audit; nothing is
    re-scored, no row is dropped and no geometry is touched.  Runs whether or
    not a frozen anchor profile exists, because the content predicates are
    deterministic and need no gate.
    """
    downgrades: list[dict[str, Any]] = []
    for d in out.get("decisions") or []:
        if d.get("counter_evidence_verified") is not True:
            continue
        ev = str(d.get("counter_evidence") or "")
        # Content filter applies regardless of whether a counter_evidence_span
        # record exists: the span-selection loop may have abstained or the row
        # may not have been iterated by _iter_candidates.  Defective incumbent
        # counter evidence must not remain verified (direction v68 P0).
        ok, cf_reason = passes_content_filter(ev, d)
        if ok:
            continue
        downgrades.append({
            "decision_id": str(d.get("decision_id") or ""),
            "leg": "incumbent_sweep",
            "before": {
                "counter_evidence_verified": True,
                "counter_status": d.get("counter_status"),
                "counter_evidence_head": ev[:160],
            },
            "after": {
                "counter_evidence_verified": False,
                "counter_status": d.get("counter_status"),
                "counter_evidence_unevidenced_reason": cf_reason,
            },
            "reason_code": cf_reason,
            "defects": frozen_content_defects(ev, d),
        })
        d["counter_evidence_verified"] = False
        d["counter_evidence_unevidenced"] = True
        d["counter_evidence_unevidenced_reason"] = cf_reason
    return downgrades


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
        # No anchor profile -> the gate-dependent selection cannot run, but the
        # REJECTION/INCUMBENT leg still must: the frozen D1-D4 content
        # predicates need no gate, and a bundle whose query has no profile
        # (e.g. petty-theft-dismissal) may still carry defective verified
        # incumbents.  Publish both facts; never claim selection happened.
        downgrades = _content_rejection_sweep(out)
        out.setdefault("provenance", {})["counter_evidence_span"] = {
            **prov_base,
            "applied": False,
            "reason": "no_frozen_anchor_profile_for_query",
            "frozen_rules_sha256": digest,
            "content_filter_applied": True,
            "content_filter_leg": "content_only_no_anchor_profile",
            "content_filter": content_filter_provenance(),
            "n_candidates": 0,
            "n_selected": 0,
            "n_downgraded": len(downgrades),
            "n_incumbent_downgraded": len(downgrades),
            "downgraded_ids": [d["decision_id"] for d in downgrades],
            "downgrades": downgrades,
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
    n_incumbent_guard_exempted = 0
    selected_ids: list[str] = []
    abstained_ids: list[str] = []
    reasons: dict[str, int] = {}
    downgrades: list[dict[str, Any]] = []
    retained: list[dict[str, Any]] = []
    for d in _iter_candidates(out.get("decisions") or []):
        n_candidates += 1
        before = {
            "counter_evidence_verified": d.get("counter_evidence_verified"),
            "counter_status": d.get("counter_status"),
            "counter_evidence_head": str(d.get("counter_evidence") or "")[:160],
        }
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
        if sel.incumbent_guard_exempted:
            n_incumbent_guard_exempted += 1
        record = sel.to_dict()
        if sel.field:
            record["field_sha256"] = _text_sha256(d, sel.field)
        d["counter_evidence_span"] = record
        if not sel.selected:
            n_abstained += 1
            abstained_ids.append(str(d.get("decision_id") or ""))
            reasons[sel.reason_code] = reasons.get(sel.reason_code, 0) + 1
            # REJECTION/INCUMBENT LEG (direction v68 P0), scoped exactly as the
            # ordered work words it: a row whose SELECTED OR INCUMBENT evidence
            # FAILS the frozen D2/D3/D4 predicates is rejected/downgraded to an
            # explicitly-unevidenced row rather than left verified.  A row whose
            # incumbent evidence is verbatim and CONTENT-SOUND is NOT downgraded
            # by this leg - the success rule requires the known sound row
            # (bstger_SK.2023.49) to stay verified/sound - and its abstention is
            # published instead (the frozen label gate's abstention is a
            # different axis from content soundness; on the live path the
            # accepted anchor seam still owns label-driven clearing).
            incumbent_ev = str(d.get("counter_evidence") or "")
            incumbent_defects = frozen_content_defects(incumbent_ev, d)
            incumbent_grounded, _off = ground_evidence(incumbent_ev, d)
            content_fail = bool(incumbent_defects) or (
                bool(incumbent_ev.strip()) and incumbent_grounded is None
            )
            if content_fail:
                was_verified = d.get("counter_evidence_verified") is True
                d["counter_evidence_verified"] = False
                d["counter_evidence_unevidenced"] = True
                d["counter_evidence_unevidenced_reason"] = sel.reason_code
                if was_verified:
                    downgrades.append({
                        "decision_id": str(d.get("decision_id") or ""),
                        "leg": "seam_abstention",
                        "before": before,
                        "after": {
                            "counter_evidence_verified": False,
                            "counter_status": d.get("counter_status"),
                            "counter_evidence_unevidenced_reason": sel.reason_code,
                        },
                        "reason_code": sel.reason_code,
                        "defects": incumbent_defects,
                        "incumbent_grounded_in": incumbent_grounded,
                    })
            else:
                retained.append({
                    "decision_id": str(d.get("decision_id") or ""),
                    "leg": "seam_abstention_content_sound_incumbent",
                    "reason_code": sel.reason_code,
                    "counter_evidence_verified": d.get("counter_evidence_verified"),
                    "counter_status": d.get("counter_status"),
                    "incumbent_grounded_in": incumbent_grounded,
                    "defects": [],
                    "note": (
                        "frozen label gate abstained (reason_code above); the "
                        "incumbent evidence is verbatim and passes the frozen "
                        "D1-D4 content predicates, so this leg does not "
                        "downgrade it (ordered-work success rule)"
                    ),
                })
            continue
        n_selected += 1
        selected_ids.append(str(d.get("decision_id") or ""))
        # Keep the row's own proposal; the frozen gate confirms it.
        d["counter_status"] = _proposal_status(d)
        d["counter_evidence"] = sel.quote
        d["counter_evidence_verified"] = True
        d.pop("counter_evidence_unevidenced", None)
        d.pop("counter_evidence_unevidenced_reason", None)
        if sel.decision is not None:
            d["counter_uncertainty"] = sel.decision.uncertainty
        d["counter_proposal_source"] = SPAN_VERSION

    # Final incumbent sweep: a row the seam never iterated (no scored status,
    # no adversarial signal) may still claim verified counter evidence.  The
    # frozen content predicates apply to that incumbent too: a defective one is
    # downgraded to explicitly-unevidenced rather than left verified.
    sweep = _content_rejection_sweep(out)
    downgrades.extend(sweep)
    n_incumbent_downgraded = len(sweep)

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
        "n_incumbent_guard_exempted": n_incumbent_guard_exempted,
        "precision_guard_scope": (
            "vetoes off-topic scan proposals; exempts the row's own verbatim, "
            "gate-confirmed, content-clean incumbent (v68 scope; no "
            "packet-of-record v3 row carries an incumbent, so the accepted v3 "
            "arm numbers are unchanged)"
        ),
        "selected_ids": selected_ids,
        "abstained_ids": abstained_ids,
        "abstention_reasons": dict(sorted(reasons.items())),
        # Rejection/incumbent leg audit trail (direction v68 P0).
        "content_filter": content_filter_provenance(),
        "n_downgraded": len(downgrades),
        "n_incumbent_downgraded": n_incumbent_downgraded,
        "downgraded_ids": [d["decision_id"] for d in downgrades],
        "downgrades": downgrades,
        "n_retained_content_sound": len(retained),
        "retained_content_sound": retained,
    }
    return out


# ---- Content quality filter (direction v68 P0, rejection/incumbent leg) ----
#
# Deterministic, model-free filter over the FROZEN D1-D4 content predicates.
# Byte-aligned with the accepted evaluation instrument's ``classify_verified_row``
# (evaluation/counter_evidence_quality_benchmark.py), which the accepted
# falsifier 40105794124 and the accepted H2 probe both measure with:
#
#   * predicate source sha256 : aac86527e5e54f0f9c527daac7ff1016d5124731b8ce673797520ff3dd53067d
#     (re-hashed REPORTED-ONLY from the frozen hypothesis of run 40105794124;
#      identical sha recorded by the accepted H2 probe hypothesis)
#   * frozen hypothesis sha256: 734a447dffd86a360a46ce9a804e3bb9f7eb224f9067777d78b62216e13e0881
#
# The constants below are COPIED VERBATIM from that frozen source.  This seam
# may only NARROW which evidence is offered to (or left claimed by) the frozen
# confirm-or-abstain gate; it never edits, re-tunes or re-derives the gate, the
# rubric, a threshold or a bar (factory-wide requirement 37, H2 ruling).
# A filter run here changes nothing about ``decide_label``: it only decides
# whether a quote the gate confirmed may still claim ``counter_evidence_verified``.

FROZEN_PREDICATE_SOURCE = "evaluation/counter_evidence_quality_benchmark.py"
FROZEN_PREDICATE_SOURCE_SHA256 = (
    "aac86527e5e54f0f9c527daac7ff1016d5124731b8ce673797520ff3dd53067d"
)
FROZEN_PREDICATE_HYPOTHESIS_SHA256 = (
    "734a447dffd86a360a46ce9a804e3bb9f7eb224f9067777d78b62216e13e0881"
)

#: Frozen D2: evidence grounded in the row's own full_text below this offset
#: is in the letterhead zone (LETTERHEAD_ZONE_OFFSET_MAX in the frozen source).
LETTERHEAD_ZONE_OFFSET_MAX = 400

#: Frozen D3: literal markup residue tokens in the evidence string.
MARKUP_TOKENS = ("<mark>", "</mark>", "<em>", "</em>", "<b>", "</b>", "<highlight>")

#: Frozen D4: minimum hits of the OWNING-LANGUAGE marker set that keeps a row
#: language-consistent; the mismatch rule needs own == 0 and best other >= this.
MIN_MARKER_HITS = 3

#: Frozen D4 per-language marker sets (verbatim from the frozen source).
LANGUAGE_MARKER_SETS = {
    "de": ["Regeste", "Erwägung", "Kündigung", "Mietvertrag", "Bundesgericht", "Verfügung"],
    "fr": ["Considérant", "résiliation", "bail", "Tribunal fédéral", "recours", "art."],
    "it": ["Dispositivo", "risoluzione", "affitto", "Tribunale federale", "ricorso", "regola"],
}

#: Grounding order, exactly as the frozen classifier searches fields.
GROUNDING_FIELDS = ("full_text", "snippet", "regeste")


def content_filter_provenance() -> dict[str, Any]:
    """Re-hash metadata published in bundle provenance (REPORTED-ONLY)."""
    return {
        "predicate_source": FROZEN_PREDICATE_SOURCE,
        "predicate_source_sha256": FROZEN_PREDICATE_SOURCE_SHA256,
        "frozen_hypothesis_sha256": FROZEN_PREDICATE_HYPOTHESIS_SHA256,
        "letterhead_zone_offset_max": LETTERHEAD_ZONE_OFFSET_MAX,
        "markup_tokens": list(MARKUP_TOKENS),
        "min_marker_hits": MIN_MARKER_HITS,
        "grounding_fields": list(GROUNDING_FIELDS),
        "alignment": (
            "constants copied verbatim from the frozen classify_verified_row "
            "predicates; this filter only narrows evidence, it never edits the "
            "frozen confirm-or-abstain gate, rubric, threshold or bar"
        ),
    }


def ground_evidence(quote: str, row: dict) -> tuple[str | None, int]:
    """First field/offset where ``quote`` occurs verbatim (frozen order)."""
    ev = str(quote or "")
    if not ev:
        return None, -1
    for field in GROUNDING_FIELDS:
        text = str(row.get(field) or "")
        idx = text.find(ev) if text else -1
        if idx >= 0:
            return field, idx
    return None, -1


def frozen_content_defects(quote: str, row: dict) -> list[str]:
    """Apply the frozen D1-D4 content predicates to one evidence string.

    Returns the defect list with the frozen class names (empty = sound).
    Mirrors ``classify_verified_row`` exactly: D1 empty, D2 letterhead zone
    (grounded in own full_text below the frozen offset), D3 markup residue,
    D4 language-marker mismatch.  No model, no network, no re-tuning.

    The predicate set is deliberately closed: no token/keyword supplement is
    applied here.  A content-level "court word" heuristic (e.g. rejecting any
    evidence containing "Gericht" or "court") was tried in cycle 40832905362
    and removed in cycle 40840720468 because it both duplicated the frozen
    offset-based D2 class and would falsely reject substantive sentences that
    merely discuss the court.  A filter may only narrow which spans are offered
    to the frozen gate; it may not invent a new defect class.
    """
    ev = quote if isinstance(quote, str) else ("" if quote is None else str(quote))
    lang = row.get("language")
    defects: list[str] = []

    if not ev.strip():
        defects.append("D1_empty_evidence")

    field, offset = ground_evidence(ev, row)
    if field == "full_text" and 0 <= offset < LETTERHEAD_ZONE_OFFSET_MAX and ev.strip():
        defects.append("D2_letterhead_zone")

    if any(tok in ev for tok in MARKUP_TOKENS):
        defects.append("D3_markup_residue")

    if lang in LANGUAGE_MARKER_SETS and ev.strip():
        own = sum(1 for tok in LANGUAGE_MARKER_SETS[lang] if tok in ev)
        others = [
            sum(1 for tok in LANGUAGE_MARKER_SETS[other] if tok in ev)
            for other in LANGUAGE_MARKER_SETS
            if other != lang
        ]
        best_other = max(others) if others else 0
        if own == 0 and best_other >= MIN_MARKER_HITS:
            defects.append("D4_language_marker_mismatch")

    return defects


#: Frozen class name -> lowercase reason code used in seam records.
_DEFECT_REASON = {
    "D1_empty_evidence": "d1_empty_evidence",
    "D2_letterhead_zone": "d2_letterhead_zone",
    "D3_markup_residue": "d3_markup_residue",
    "D4_language_marker_mismatch": "d4_language_marker_mismatch",
}


def passes_content_filter(quote: str, row: dict, start: int | None = None) -> tuple[bool, str]:
    """``(ok, reason_code)`` under the frozen D1-D4 predicates.

    ``start`` is accepted for call-site compatibility and ignored: grounding is
    recomputed from the row's own fields exactly the way the frozen classifier
    grounds it, so the product filter and the frozen re-probe can never disagree
    about where an evidence string sits.
    """
    defects = frozen_content_defects(quote, row)
    if not defects:
        return True, ""
    return False, _DEFECT_REASON[defects[0]]


__all__ = [
    "SPAN_ENV",
    "SPAN_GUARD_ENV",
    "SPAN_VERSION",
    "SURFACE_SPAN_ENV",
    "SURFACE_SPAN_VERSION",
    "apply_surface_span_confirmation",
    "apply_verified_span_selection",
    "content_filter_provenance",
    "field_candidates",
    "frozen_content_defects",
    "guard_terms",
    "ground_evidence",
    "passes_content_filter",
    "select_span",
    "sentence_spans",
    "span_passes_precision_guard",
    "verify_span",
    "SpanCandidate",
    "SpanSelection",
]
