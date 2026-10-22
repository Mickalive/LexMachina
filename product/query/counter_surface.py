"""Pool counter-surface scan (product-owned) — direction v63 ordered item 7(a).

Why this module exists
----------------------
Factory direction v63 records the accepted cached counter-surface falsification
(product measurement, anchor run 39838415410): on the cached offline path
**0 of 14** known authorities were signalled, only **5 of 14** were hydrated,
and **3 of 5** hydrated rows carried a heuristic signal.  The two named remedy
candidates are exactly what this module implements, both bounded and both
disclosure-only:

1. **Broader hydration.**  The shipped counter surface only ever classified
   rows that reached the map through the adversarial probes.  A known
   authority that the *initial* pass already retrieved (by far the common
   case on a cached replay) was never examined for limitation markers at all,
   and was hydrated only if it happened to sit inside the answer's evidence
   subset.  The scan hydrates a bounded, marker-preferring subset of the
   rendered pool and classifies every row that has any text.
2. Lexicon alignment.  The planner's ``EVIDENCE_MARKERS`` stay byte-stable at
   ``adversarial_retrieval/3`` (Core Evaluation re-freezes against planner sha
   9764a37e..., so the planner must not drift).  The scan uses
   :data:`ALIGNED_MARKERS`: a small, conservative set of additional
   limitation/disagreement phrasings attested in DE/FR/IT Swiss decisions
   that the frozen planner lexicon does not carry (``anderer Auffassung``,
   ``nicht zu teilen``, ``bis anhin`` …), plus two precision guards the
   planner does not own (measured on the rent-default offline slice, where
   5 of 6 raw surface signals were the French ``sauf`` firing inside the
   German compound ``Zahlungsaufforderung``): short markers (<= 5 chars) are
   word-boundary-checked in the evidence sentence
   (:func:`attested_markers`), and a dismissal narration licenses no signal
   for ANY intent, not only for ``contrary``
   (:func:`_disposal_narration`).

What this module never does
---------------------------
* it never writes ``counter_status`` / ``counter_evidence`` / ``counter_uncertainty``
  — those scored fields stay the exclusive product of the accepted
  counter-emission-repair + anchor-classifier path;
* it never touches geometry, ranks, clusters or relations;
* it never asserts that any decision IS supporting/contrary/limiting: the
  signal is a heuristic *surface* (verbatim evidence sentence + markers
  recorded per row), an exploration aid for the map, not a legal label;
* it never re-derives a frozen rubric, bar or threshold, and it never hits the
  network (live/fixture hydration goes through the existing cache-first
  retrieval seams).

The field it writes is deliberately named ``counter_surface_signal`` — NOT
``adversarial_retrieval_signal`` — so the accepted emission-repair population
(adversarial-survivor proposals) is untouched by construction.
"""
from __future__ import annotations

import copy
import os
import re
from typing import Any, Callable, Iterable

from .adversarial_retrieval import (
    COUNTER_STATUS_BY_INTENT,
    DISPOSAL_SENTENCE_PATTERNS,
    EVIDENCE_MARKERS,
    INTENT_ORDER,
    _sentence_eligible,
    bundle_topic_terms,
)
from .answer import split_sentences

#: Bump whenever the aligned lexicon, the hydration selection rule or the
#: written field shape changes.  Never reuse an old value for new behaviour.
COUNTER_SURFACE_VERSION = "counter_surface/1"

#: Env kill-switch (default on).  ``off`` records a skipped provenance block
#: and changes nothing, so an auditor can diff a scanned vs unscanned bundle.
ENABLE_ENV = "LEXMACHINA_COUNTER_SURFACE"

#: Lexicon alignment (direction v63 item 7(a)).  Additive ONLY: every entry is
#: checked disjoint from the frozen planner markers of the same intent by
#: ``test_counter_surface.py``.  Chosen for precision under the existing
#: sentence guards (topic term present, no Eintretens boilerplate, no
#: dismissal narration for the contrary intent): disagreement formulations and
#: genuine departure/reservation phrasings, never disposal words.
ALIGNED_MARKERS: dict[str, tuple[str, ...]] = {
    "exception": (
        "ausnahme hiervon",   # DE carve-out after a stated rule
        "behaltlich",         # DE/CH "subject to" (attested BGer phrasing)
        "fatte salve",        # IT "without prejudice to"
    ),
    "contrary": (
        "anderer auffassung",          # DE "of a different view"
        "nicht zu teilen",             # DE "dieser Auffassung ist nicht beizutreten / nicht zu teilen"
        "kann nicht gefolgt werden",   # DE "cannot be followed"
        "cependant",                   # FR turn marker introducing the court's own view
        "néanmoins",                   # FR "nevertheless"
        "tuttavia",                    # IT "however"
        "dévier",                      # FR "dévier de cette jurisprudence"
        "discostarsi",                 # IT "discostarsi da questa giurisprudenza"
    ),
    "minority": (),
    "older_line": (
        "bis anhin",                   # DE/CH "until now" (older line)
        "bisherige rechtsprechung",    # DE "the hitherto case-law"
    ),
}


def combined_markers(intent: str) -> tuple[str, ...]:
    """Frozen planner markers + aligned additions for one intent (deterministic)."""
    base = tuple(EVIDENCE_MARKERS.get(intent, ()))
    extra = tuple(ALIGNED_MARKERS.get(intent, ()))
    return base + extra


def probe_text(row: dict) -> str:
    """Best available text for a rendered row (full body, else abstract, else snippet)."""
    for key in ("full_text", "regeste", "snippet", "title"):
        text = str(row.get(key) or "").strip()
        if text:
            return text
    return ""


def _text_source(row: dict) -> str:
    for key in ("full_text", "regeste", "snippet", "title"):
        if str(row.get(key) or "").strip():
            return key
    return "none"


def marker_bearing(text: str) -> str | None:
    """First aligned-or-frozen marker present in ``text`` (lowercased match), else None."""
    low = (text or "").lower()
    if not low:
        return None
    for intent in INTENT_ORDER:
        for marker in combined_markers(intent):
            if marker in low:
                return marker
    return None


#: Short-marker boundary guard.  The frozen planner lexicon matches by plain
#: substring, so the French ``sauf`` fires inside the German compound
#: ``Zahlungsaufforderung`` (``Zahlungs-au-forderung``) — measured on the
#: rent-default offline slice, where 5 of 6 surface signals were exactly this
#: compound collision.  The planner stays byte-stable (evaluation re-freezes
#: against its sha), so the scan owns the precision fix: markers of length <= 5
#: must appear as their own word in the evidence sentence, longer markers keep
#: the planner's morphology-tolerant substring rule.
_SHORT_MARKER_MAX = 5
_MARKER_WORD_RE = {
    marker: re.compile(
        r"(?<![a-zäöüßéèêàâîôûùç])" + re.escape(marker) + r"(?![a-zäöüßéèêàâîôûùç])",
        re.IGNORECASE,
    )
    for intent in INTENT_ORDER
    for marker in combined_markers(intent)
    if len(marker) <= _SHORT_MARKER_MAX
}


def attested_markers(sentence: str, markers: Iterable[str]) -> list[str]:
    """Markers of the candidate set actually attested in ``sentence``.

    Applies the short-marker word-boundary rule above; longer markers keep the
    planner's substring semantics.  Deterministic, order-preserving.
    """
    low = (sentence or "").lower()
    out: list[str] = []
    for marker in markers:
        pattern = _MARKER_WORD_RE.get(marker)
        if pattern is not None:
            if pattern.search(low):
                out.append(marker)
        elif marker in low:
            out.append(marker)
    return out


def _disposal_narration(sentence: str) -> bool:
    """True when the sentence narrates a rejected appeal (audit D2 class).

    The frozen planner applies this guard only to the ``contrary`` intent; the
    scan applies it to EVERY intent, because a disposal narration licenses no
    counter surface at all — "the appeal was rejected, the ruling stood" is the
    opposite of counter-authority whichever intent proposed it.
    """
    low = (sentence or "").lower()
    return any(p.search(low) for p in DISPOSAL_SENTENCE_PATTERNS)


def select_for_hydration(rows: Iterable[dict], *, hydrate_top: int) -> list[str]:
    """Bounded, marker-preferring hydration selection over unhydrated rows.

    Selection rule (deterministic): rows without ``full_text`` whose current
    probe text already carries a limitation marker come first (they are the
    rows a scan can actually signal with one cheap detail fetch), then the
    remaining rows by rank fill any leftover budget.  Ordered by rank within
    each group.  ``hydrate_top`` is a hard cap — the scan never grows the
    hydration budget the product already spends.
    """
    cap = max(0, int(hydrate_top))
    if cap == 0:
        return []
    unhydrated = [r for r in rows if not str(r.get("full_text") or "").strip()]
    marker_rows = [r for r in unhydrated if marker_bearing(probe_text(r))]
    marker_ids = {str(r.get("decision_id")) for r in marker_rows}
    plain_rows = [r for r in unhydrated
                  if str(r.get("decision_id")) not in marker_ids]

    def _rank(row: dict) -> tuple[int, str]:
        try:
            rank = int(row.get("rank") or 10**9)
        except (TypeError, ValueError):
            rank = 10**9
        return (rank, str(row.get("decision_id") or ""))

    marker_rows.sort(key=_rank)
    plain_rows.sort(key=_rank)
    chosen = (marker_rows + plain_rows)[:cap]
    return [str(r.get("decision_id") or "") for r in chosen if r.get("decision_id")]


def scan_classify(
    text: str,
    intent: str,
    *,
    topic_terms: list[str] | tuple[str, ...] | None = None,
) -> tuple[str | None, str, list[str], str | None]:
    """Mirror of the frozen labelling rule over the COMBINED lexicon.

    ``adversarial_retrieval.classify_against_intent`` only matches the frozen
    ``EVIDENCE_MARKERS`` (the planner stays byte-stable at
    ``adversarial_retrieval/3``), so the aligned markers need a matching
    classifier.  This function reuses the frozen rule's own sentence machinery
    (``split_sentences``, ``_sentence_eligible`` incl. its boilerplate guard,
    the fixed ``probe_first`` intent order, the topical-term gate and the
    line-level fallback) and only substitutes the marker set with
    :func:`combined_markers`, plus the two scan-owned precision guards.

    Returns ``(status, evidence, markers, matched_intent)`` or
    ``(None, "", [], None)``.  Never asserts a legal label beyond the
    heuristic status vocabulary the frozen rule itself uses.
    """
    lowered = (text or "").lower()
    topical = [str(t).lower() for t in (topic_terms or []) if str(t).strip()]
    if not lowered or not topical:
        return None, "", [], None
    probe_first = [intent] + [i for i in INTENT_ORDER if i != intent]
    for candidate_intent in probe_first:
        markers = [m for m in combined_markers(candidate_intent) if m in lowered]
        if not markers:
            continue
        status = COUNTER_STATUS_BY_INTENT.get(candidate_intent, "candidate-limiting")
        for sentence in split_sentences(text):
            low = sentence.lower()
            if not _sentence_eligible(sentence, markers, intent=candidate_intent):
                continue
            if not any(t in low for t in topical):
                continue
            kept = attested_markers(sentence, markers)
            if not kept or _disposal_narration(sentence):
                continue
            return status, sentence[:400], kept[:6], candidate_intent
        for line in (text or "").splitlines():
            if not _sentence_eligible(line, markers, intent=candidate_intent):
                continue
            low = line.lower()
            if not any(t in low for t in topical):
                continue
            kept = attested_markers(line, markers)
            if not kept or _disposal_narration(line):
                continue
            anchor = line.strip()
            if anchor:
                return status, anchor[:400], kept[:6], candidate_intent
    return None, "", [], None


def _classify_row(row: dict, topic_terms: list[str]) -> dict[str, Any] | None:
    """First supported signal for one row across the fixed intent order, or None.

    Two scan-owned precision guards are applied on top of the mirrored rule
    (which itself already applies them per sentence): short markers are
    word-boundary-checked, and a dismissal narration licenses no signal for
    ANY intent.
    """
    text = probe_text(row)
    if not text or not topic_terms:
        return None
    # One call is enough: scan_classify's probe_first covers the fixed
    # INTENT_ORDER from the requested intent, exactly like the frozen rule.
    status, evidence, markers, matched = scan_classify(
        text, INTENT_ORDER[0], topic_terms=topic_terms
    )
    if status and evidence and matched:
        return {
            "component": COUNTER_SURFACE_VERSION,
            "heuristic_status": status,
            "intent": matched,
            "evidence": evidence,
            "markers": list(markers),
            "text_source": _text_source(row),
        }
    return None


def scan_counter_surface(
    bundle: dict,
    *,
    hydrate: Callable[[list[str]], dict[str, str]] | None = None,
    hydrate_top: int = 8,
    topic_terms: list[str] | None = None,
) -> dict:
    """Return a NEW bundle with ``counter_surface_signal`` + provenance.

    Pure and deterministic given ``bundle`` bytes and the ``hydrate`` callback
    (may be None: the scan then works from the text already on the rows).
    Never mutates the input, never writes scored counter fields, never moves
    geometry.
    """
    out = copy.deepcopy(bundle)
    decisions: list[dict] = out.get("decisions") or []
    terms = list(topic_terms) if topic_terms is not None else bundle_topic_terms(out)

    n_unhydrated = sum(1 for d in decisions if not str(d.get("full_text") or "").strip())
    n_marker_bearing = sum(
        1 for d in decisions
        if not str(d.get("full_text") or "").strip() and marker_bearing(probe_text(d))
    )
    selected = select_for_hydration(decisions, hydrate_top=hydrate_top)
    hydrated: dict[str, str] = {}
    hydrate_error: str | None = None
    if selected and hydrate is not None:
        try:
            hydrated = dict(hydrate(selected) or {})
        except Exception as exc:  # a scan failure must never cost the bundle
            hydrate_error = f"{type(exc).__name__}: {exc}"
            hydrated = {}
    by_id = {str(d.get("decision_id")): d for d in decisions}
    for did, text in hydrated.items():
        row = by_id.get(did)
        if row is not None and text:
            row["full_text"] = text

    n_signalled = 0
    signalled_ids: list[str] = []
    intent_histogram: dict[str, int] = {}
    status_histogram: dict[str, int] = {}
    for row in decisions:
        signal = _classify_row(row, terms)
        if signal is None:
            row.pop("counter_surface_signal", None)
            continue
        row["counter_surface_signal"] = signal
        n_signalled += 1
        signalled_ids.append(str(row.get("decision_id") or ""))
        intent_histogram[signal["intent"]] = intent_histogram.get(signal["intent"], 0) + 1
        status = signal["heuristic_status"]
        status_histogram[status] = status_histogram.get(status, 0) + 1

    out.setdefault("provenance", {})["counter_surface"] = {
        "component": COUNTER_SURFACE_VERSION,
        "n_rows": len(decisions),
        "n_unhydrated_before": n_unhydrated,
        "n_marker_bearing_unhydrated": n_marker_bearing,
        "hydrate_top": max(0, int(hydrate_top)),
        "n_selected_for_hydration": len(selected),
        "selected_for_hydration": selected,
        "n_hydrated": len(hydrated),
        "hydrated_ids": sorted(hydrated),
        "hydrate_error": hydrate_error,
        "n_signalled": n_signalled,
        "signalled_ids": signalled_ids,
        "intent_histogram": dict(sorted(intent_histogram.items())),
        "counter_surface_status_histogram": dict(sorted(status_histogram.items())),
        "aligned_markers": {
            intent: list(markers) for intent, markers in ALIGNED_MARKERS.items() if markers
        },
        "precision_guards": [
            "short_markers_word_boundary_checked (<=5 chars, e.g. FR 'sauf' "
            "must not fire inside the DE compound 'Zahlungsaufforderung')",
            "dismissal narration licenses no signal for ANY intent "
            "(planner guards this only for the contrary intent)",
        ],
        "writes_scored_counter_fields": False,
        "claim_ceiling": (
            "heuristic counter-surface scan over the rendered pool: a row is "
            "signalled only when a verbatim sentence of its own text carries a "
            "limitation marker (frozen planner lexicon + disclosed aligned "
            "additions), shares a topical term with the answer/query, and is "
            "neither procedural boilerplate nor a dismissal narration. The "
            "signal is an exploration surface for the map — it NEVER writes "
            "counter_status, never asserts that a decision IS supporting/"
            "contrary/limiting, and never touches geometry, ranks or clusters; "
            "the scored counter fields remain the exclusive product of the "
            "accepted emission-repair + anchor-classifier path"
        ),
    }
    return out


def apply_counter_surface(
    bundle: dict,
    *,
    retrieval_mode: str = "live",
    hydrate_top: int = 8,
) -> dict:
    """Pipeline seam: cache-first hydration + scan, with the env kill-switch.

    The hydrate callback reuses the product's existing retrieval seams —
    ``pipeline._retrieve`` (cache-first, id-based on the live/offline path;
    fixture replay hydrates from the recorded envelopes).  No new network
    client, no new cache, no legacy 174k representation is touched.
    """
    mode = os.environ.get(ENABLE_ENV, "").strip().lower()
    if mode == "off":
        out = copy.deepcopy(bundle)
        out.setdefault("provenance", {})["counter_surface"] = {
            "component": COUNTER_SURFACE_VERSION,
            "skipped": True,
            "skip_reason": f"{ENABLE_ENV}=off",
            "writes_scored_counter_fields": False,
        }
        return out

    query = str(bundle.get("query") or "")
    n_rows = len(bundle.get("decisions") or [])

    def _hydrate(ids: list[str]) -> dict[str, str]:
        from .pipeline import _retrieve, replay_fixture_query  # lazy: no import cycle

        if retrieval_mode == "fixture":
            # Fixture replay hydrates by POSITION (top-k of the replay order),
            # not by id, and the bundle's rank order differs from the replay
            # order after rerank/merge — so hydrate the whole replayed set
            # (local JSON only, no network) and pick the selected ids from it.
            # top_n MUST stay the bundle's own size: the adapter's cache keys
            # are config-shaped, and a differently-sized config misses the
            # recorded envelopes (measured: top_n=200 -> 0 candidates where
            # top_n=100 -> 165).
            sub = replay_fixture_query(query, top_n=max(1, n_rows), hydrate_top=200)
        else:
            sub = _retrieve(query, max(1, n_rows), mode=retrieval_mode,
                            hydrate_top=0, hydrate_ids=list(ids))
        by_id = {str(c.get("decision_id")): c for c in sub.get("candidates") or []}
        out: dict[str, str] = {}
        for did in ids:
            text = str((by_id.get(did) or {}).get("full_text") or "")
            if text:
                out[did] = text
        return out

    return scan_counter_surface(
        bundle,
        hydrate=_hydrate,
        hydrate_top=hydrate_top,
    )


__all__ = [
    "ALIGNED_MARKERS",
    "COUNTER_SURFACE_VERSION",
    "ENABLE_ENV",
    "apply_counter_surface",
    "attested_markers",
    "combined_markers",
    "marker_bearing",
    "probe_text",
    "scan_classify",
    "scan_counter_surface",
    "select_for_hydration",
]
