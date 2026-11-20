"""Sourced-answer obligations on the runnable query path (QUERY_MAP_MVP 8).

Two product requirements in the canonical spec are *not* satisfied by the
shipped path today, and both are satisfiable without a model, a network call or
a paid dependency:

1. **The deterministic path must ship a sourced answer.**
   ``run_generative_audit(fixture_mode=True)`` is handed the literal header
   ``"Fixture grounded answer [a] [b]"`` and the fixture provider returns it
   verbatim (``frontier-generative-audit`` provider ``_fixture_result``).  The
   query page renders ``answer.prose`` only, so the demo/offline path - the one
   an owner clicks first - showed two bracketed identifiers and no legal
   content.  :func:`build_fixture_answer` keeps that header (it is the honest
   provenance marker for "no model ran") and appends **verbatim passages from
   the very decisions the answer already cites**.

2. **The answer must mention the counter-authorities the independent pass
   surfaced** (QUERY_MAP_MVP 8, bullet 4).  Nothing after the counter stages
   ever touches ``answer.prose``, so a jurist reading only the answer panel was
   never told that a limiting/contrary authority exists in the result set.
   :func:`apply_counter_authority_note` appends that section.

Contract, deliberately narrow
-----------------------------
Both writers touch **only** ``bundle["answer"]["prose"]`` and their own
``bundle["provenance"]`` blocks.  They never write ``counter_status``,
``counter_evidence``, ``counter_evidence_verified``, ``counter_uncertainty``,
geometry, ranks, clusters or relations; they never read or edit a frozen rubric,
threshold, gate or bar; and they assert nothing the row itself does not already
carry.  Every ``[...]`` marker they add is a ``decision_id`` that is present in
the bundle, so ``product/answer_reliability.py::prose_citation_validity`` stays
resolved and ``validate_bundle``'s citation boundary is unchanged.

Quotes follow the accepted convention of ``product/query/answer_contract.py``:
a verbatim sentence with markup stripped, attributed with ``[decision_id]`` and
the row's own citation string.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any

from .answer_contract import _clean, _sentences, norm
from .answer_gap import detect_language
from .concept_coverage import concept_prefix, content_concepts
from .counter_status import is_counter_status

#: Version stamps exported into provenance so an auditor can tell which writer
#: produced a given prose block without diffing prose against a historical file.
FIXTURE_SOURCE_VERSION = "fixture_sourced_answer/1"
COUNTER_NOTE_VERSION = "answer_counter_note/1"

#: Bounds are small on purpose: the answer is a reading aid, the map is the
#: audit surface.  QUERY_MAP_MVP 8 asks for "concise", and every extra quote is
#: one more thing that must stay verbatim-true.
MAX_FIXTURE_QUOTES = 4
MAX_COUNTER_ROWS = 8
MAX_QUOTE_CHARS = 320

#: Section headings and per-row wording in the four languages the product
#: already answers in (``answer_gap._TEXT`` uses the same table shape).
_TEXT: dict[str, dict[str, str]] = {
    "de": {
        "sourced": ("Wörtlich belegte Fundstellen aus den abgerufenen "
                    "Entscheiden (extrahiert, keine Rechtsberatung):"),
        "quote_suffix": "kein zitierfähiger Beleg gesetzt",
        "unverified": "Beleg NICHT als wörtlich bestätigt (unevidenced)",
        "verified": "Beleg als wörtlich bestätigt (verified)",
        "counter": "Gegenstimmen / einschränkende Entscheide im Ergebnis",
    },
    "fr": {
        "sourced": ("Passages cités mot pour mot dans les décisions "
                    "récupérées (extrait, pas un conseil juridique) :"),
        "quote_suffix": "aucun fondement citable retenu",
        "unverified": "fondement NON confirmé mot pour mot (unevidenced)",
        "verified": "fondement confirmé mot pour mot (verified)",
        "counter": "Voix contraignantes / décisions limitatives dans le résultat",
    },
    "it": {
        "sourced": ("Passaggi citati alla lettera nelle decisioni recuperate "
                    "(estratto, non un parere legale):"),
        "quote_suffix": "nessun fondamento citabile selezionato",
        "unverified": "fondamento NON confermato alla lettera (unevidenced)",
        "verified": "fondamento confermato alla lettera (verified)",
        "counter": "Voci contrarie / decisioni limitative nel risultato",
    },
    "en": {
        "sourced": ("Verbatim passages from the retrieved decisions "
                    "(extracted, not legal advice):"),
        "quote_suffix": "no citable evidence set",
        "unverified": "evidence NOT verbatim-confirmed (unevidenced)",
        "verified": "evidence verbatim-confirmed (verified)",
        "counter": "Counter-authorities / limiting decisions in this result set",
    },
}

#: ``answer_contract._sentences`` splits on ``[.!?;]`` + whitespace **and on
#: newlines** on purpose (it must not break ``Art. 257d Abs. 2 OR …``).  That
#: means a fragment can *begin* mid-sentence (after a line break) and can *end*
#: on a splitter artifact: a date fragment ``… vom 4. April``, a regeste
#: locator ``… (E.`` or a citation pointer ``… (lit.``.  Shipping any of those
#: as a "verbatim passage" would put a cut fragment in front of a jurist as
#: evidence, so a quote must pass all four checks below before it is eligible.
_ABBREV = {
    "lit", "abs", "art", "nr", "nrs", "vgl", "usw", "cf", "no", "vol",
    "z", "b", "d", "h", "jh", "ca", "ggf", "insb", "ed", "al", "ev",
}

#: Fields in the order a jurist reads them: body text first, then the summary,
#: then the snippet, then the title.  Earlier fields win ties, so a title
#: fragment is only quoted when the row carries nothing better.
_FIELDS = ("full_text", "regeste", "snippet", "title")


def _complete(sentence: str) -> bool:
    text = sentence.strip()
    if len(text) < 60 or len(text.split()) < 8:
        return False
    # (1) ends on a real terminator, not on a locator or a date;
    # (2) the terminator follows a lowercase letter, so ``… vom 4.`` and
    #     ``… (E.`` and ``… (lit.`` are all out;
    # (3) opens with a sentence start, so a line-broken tail is out;
    # (4) every bracket/quote it opens is closed - an unbalanced quote is the
    #     signature of a fragment cut mid-citation.
    if not text.endswith((".", "!", "?")):
        return False
    if not re.search(r"[a-zäöüà-ÿ]\.$|[!?]$", text):
        return False
    first = text[0]
    if first.islower() and first.isalpha():
        return False
    if text.rsplit(".", 1)[0].split()[-1].strip("(«\"[").casefold() in _ABBREV:
        return False
    for opening, closing in (("(", ")"), ("«", "»"), ('"', '"'), ("[", "]")):
        if text.count(opening) != text.count(closing):
            return False
    return True


def _shorten(sentence: str) -> str:
    if len(sentence) <= MAX_QUOTE_CHARS:
        return sentence
    cut = sentence[:MAX_QUOTE_CHARS].rsplit(" ", 1)[0]
    return cut + " …"


#: One sentence-selection rule shared by both writers: prefer a *complete*
#: sentence that touches the question's content concepts, falling back to the
#: first complete sentence the row actually carries (the same fallback the
#: historical ``results/product/reality_check/*_fixture_*.json`` artifacts
#: show).  Incomplete splits are rejected outright - a header fragment quoted
#: as evidence is worse than no quote at all.
#:
#: Matching is prefix-based (``concept_coverage.concept_prefix``), not
#: token-equality: the question's ``mietvertrag`` must reach a decision that
#: says ``Mietverhältnis``, and ``kündigung`` must reach
#: ``Kündigungssperrfrist``.  Exact token equality scored 0/47 on the shipped
#: fixture row and made the writer fall back to an off-topic sentence about
#: ``Baurecht`` - measured, not assumed.
def _pick_sentence(decision: dict, qtoks: list[str]) -> tuple[str, int] | None:
    prefixes = [p for p in (concept_prefix(tok) for tok in qtoks) if p]
    best: tuple[float, int, int, str, int] | None = None
    fallback: tuple[int, int, str] | None = None
    for rank, field in enumerate(_FIELDS):
        text = decision.get(field)
        if not text:
            continue
        for idx, sentence in enumerate(_sentences(_clean(text))):
            if not _complete(sentence):
                continue
            if fallback is None or (rank, idx) < fallback[:2]:
                fallback = (rank, idx, sentence)
            body = norm(sentence)
            overlap = sum(1 for prefix in prefixes if prefix in body)
            if not overlap:
                continue
            score = overlap / (1.0 + len(body.split()) / 60.0)
            candidate = (score, -rank, -idx, sentence, overlap)
            if best is None or candidate[:4] > best[:4]:
                best = candidate
    if best is not None:
        return _shorten(best[3]), best[4]
    if fallback is not None:
        return _shorten(fallback[2]), 0
    return None


def _cite(decision: dict) -> str:
    did = str(decision.get("decision_id") or "").strip()
    citation = str(decision.get("citation") or "").strip()
    return f"[{did}] ({citation})" if citation else f"[{did}]"


def build_fixture_answer(bundle: dict, cited_ids: list[str], header: str) -> tuple[str, dict[str, Any]]:
    """Header + verbatim passages from the decisions the fixture answer cites.

    Returns ``(prose, record)``; ``record`` belongs in
    ``provenance.answer_fixture_source``.  Degradation is explicit: a row with
    no usable text is skipped and counted, never paraphrased.
    """
    decisions = {str(d.get("decision_id") or ""): d for d in (bundle.get("decisions") or [])}
    qtoks = content_concepts(str(bundle.get("query") or ""))
    lang = detect_language(str(bundle.get("query") or ""), list(decisions.values()))
    text = _TEXT.get(lang, _TEXT["en"])

    picks: list[tuple[dict, str, int]] = []
    skipped: list[str] = []
    for did in cited_ids:
        decision = decisions.get(str(did))
        if not decision:
            skipped.append(str(did))
            continue
        picked = _pick_sentence(decision, qtoks)
        if not picked:
            # Honest degradation: this cited row carries no complete sentence
            # (a regeste that is only a title + locator, for instance).  It is
            # named in the record rather than padded with a cut fragment.
            skipped.append(str(did))
            continue
        quote, overlap = picked
        if any(norm(quote) == norm(seen) for _, seen, _ in picks):
            continue
        picks.append((decision, quote, overlap))
        if len(picks) >= MAX_FIXTURE_QUOTES:
            break

    if not picks:
        return header, {
            "version": FIXTURE_SOURCE_VERSION,
            "applied": False,
            "reason": "no_complete_sentence_in_cited_rows",
            "language": lang,
            "skipped_ids": skipped,
        }

    lines = [header, "", text["sourced"]]
    for decision, quote, _ in picks:
        lines.append(f"« {quote} » {_cite(decision)}")
    prose = "\n".join(lines).strip()
    record: dict[str, Any] = {
        "version": FIXTURE_SOURCE_VERSION,
        "applied": True,
        "language": lang,
        "n_quotes": len(picks),
        "quoted_ids": [str(d.get("decision_id") or "") for d, _, _ in picks],
        # Per-quote concept overlap is exported so an auditor can tell a quote
        # chosen for topical match from one chosen by the documented fallback.
        "quotes": [
            {
                "decision_id": str(d.get("decision_id") or ""),
                "query_concept_overlap": overlap,
                "selected_by": "query_concept" if overlap else "first_complete_sentence",
            }
            for d, _, overlap in picks
        ],
        "skipped_ids": skipped,
        "header_preserved": header,
        "quotes_sha256": hashlib.sha256(
            "\n".join(q for _, q, _ in picks).encode("utf-8")
        ).hexdigest(),
        "claim_ceiling": (
            "Verbatim passages copied from decisions already in this bundle and "
            "attributed with their own decision_id. No model ran, nothing is "
            "paraphrased, no statute is invented and no counter label is "
            "issued or implied."
        ),
    }
    return prose, record


def apply_counter_authority_note(bundle: dict) -> dict[str, Any]:
    """Append an honest counter-authority section to ``answer.prose``.

    Idempotent: a second call on the same bundle is a no-op that re-publishes
    the first call's record.  Rows are reported under the product's single
    counter predicate (``counter_status.is_counter_status``) with their own
    status and verified flag; evidence that the row does *not* report as
    verbatim-confirmed is **not** reproduced into the answer - the row stays
    inspectable on the map instead of being laundered into prose.
    """
    answer = bundle.get("answer") or {}
    prov = bundle.setdefault("provenance", {})
    existing = prov.get("answer_counter_note")
    if existing is not None:
        return existing

    record: dict[str, Any] = {
        "version": COUNTER_NOTE_VERSION,
        "applied": False,
        "reason": None,
        "rows": [],
    }
    if str(answer.get("status") or "") not in ("ready", "degraded"):
        record["reason"] = "answer_not_ready"
        prov["answer_counter_note"] = record
        return record

    decisions = bundle.get("decisions") or []
    rows = [d for d in decisions if is_counter_status(d.get("counter_status"))]
    record["n_counter_rows"] = len(rows)
    if not rows:
        record["reason"] = "no_counter_authority_rows"
        prov["answer_counter_note"] = record
        return record

    lang = detect_language(str(bundle.get("query") or ""), decisions)
    text = _TEXT.get(lang, _TEXT["en"])
    before = str(answer.get("prose") or "")

    lines = ["", text["counter"] + f" ({len(rows)}):"]
    listed: list[dict[str, Any]] = []
    for decision in rows[:MAX_COUNTER_ROWS]:
        status = str(decision.get("counter_status") or "")
        verified = decision.get("counter_evidence_verified") is True
        evidence = _clean(str(decision.get("counter_evidence") or ""))
        listed.append({
            "decision_id": str(decision.get("decision_id") or ""),
            "counter_status": status,
            "counter_evidence_verified": verified,
            "has_evidence": bool(evidence),
        })
        if verified and evidence:
            detail = f"{text['verified']}: « {evidence[:MAX_QUOTE_CHARS]} »"
        elif evidence:
            detail = f"{text['unverified']}; {text['quote_suffix']}"
        else:
            detail = text["quote_suffix"]
        lines.append(f"• {_cite(decision)} — {status}; {detail}")

    note = "\n".join(lines)
    answer["prose"] = (before.rstrip() + "\n" + note).strip()
    record.update({
        "applied": True,
        "language": lang,
        "listed": listed,
        "n_listed": len(listed),
        "n_truncated": max(0, len(rows) - MAX_COUNTER_ROWS),
        "predicate": "product.query.counter_status.is_counter_status",
        "prose_note_sha256": hashlib.sha256(note.encode("utf-8")).hexdigest(),
        "claim_ceiling": (
            "Reports each row's own counter_status and counter_evidence_verified "
            "flag as they already stand in the bundle. It issues no label, "
            "reproduces no unverified evidence, and asserts nothing about any "
            "decision beyond the row's own fields."
        ),
    })
    prov["answer_counter_note"] = record
    return record


__all__ = [
    "COUNTER_NOTE_VERSION",
    "FIXTURE_SOURCE_VERSION",
    "apply_counter_authority_note",
    "build_fixture_answer",
]
