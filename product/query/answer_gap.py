"""A sourced answer must cite something, or it must say what is missing.

Why this exists
---------------
Direction v52 backlog item (3) ships a three-question gate packet whose bundles
are re-verified for admissibility at run time.  One pre-registered question -
``de-kapitalverletzung`` - was blocked with
``answer_cites_nothing``: the generative model returned a perfectly honest
retrieval assessment ("none of the 30 retrieved decisions address the employer's
active duty of care in a capital impairment") with **zero** citations.

The previous cycle recorded the hypothesis "the answer generator must cite
retrieved decision ids".  Measuring the shipped bundle
(``product/query/concept_coverage.py``) falsifies it: the bundle holds 23 rows
on the employer's Fürsorgepflicht and **0 rows** on *Kapitalverletzung*.  The
model cited nothing because the corpus it was given does not contain the second
concept of the question.  Forcing it to cite would have put a citation on a
proposition the decision does not contain - the exact defect this lane was
audited for on the citation channel (run 38766812030).

So the product contract is the other way round:

* if the model cites, nothing here runs;
* if the model declines to cite, the product surfaces **what the corpus does
  cover, cited verbatim**, plus **an explicit statement of the concepts the
  retrieved corpus does not cover**, with the measured row counts that back it.

Both halves are checkable.  Every quoted sentence is copied verbatim from a
decision already in the bundle and is attributed with that row's own
``decision_id`` (and citation), so the answer stays inside the bundle's citation
boundary; nothing is paraphrased and no statute is invented.  The uncovered
concepts are the product's own lexical coverage measurement, exported next to
the answer so an auditor can recompute it - not prose.

The result is a ``degraded`` answer: honest, fully cited for the part of the
question the corpus supports, and explicit about the part it does not.  The
gate-admissibility check then has something real to verify, and the jurist is
never handed an uncited answer as if it were the product's answer.

Usage
-----
    from product.query.answer_gap import ensure_cited_answer
    report = ensure_cited_answer(bundle)
"""
from __future__ import annotations

import copy
import re
from typing import Any

from .answer_contract import _sentences  # same sentence machinery as the fills
from .concept_coverage import (
    concept_prefix, coverage_report, decision_text, norm, rows_for_concept,
)

#: Report schema, so a consumer can pin it.
SCHEMA = "product-answer-gap-contract/1"

#: How many covered concepts get their own cited quote block.
MAX_QUOTED_CONCEPTS = 3

#: How many decisions are quoted per concept.
MAX_ROWS_PER_CONCEPT = 2

#: Longest single verbatim quote (long enough to be attestable, short enough to read).
MAX_QUOTE_CHARS = 420

#: Smallest quote: below this a "sentence" is a fragment, and the answer would be
#: quoting fragments to look grounded.
MIN_QUOTE_CHARS = 60

#: Language markers used to answer in the researcher's language.  Deliberately
#: short and explicit: guessing the wrong language is worse than falling back.
_LANG_MARKERS = {
    "de": {"der", "die", "das", "und", "bei", "für", "fuer", "welche", "welchen", "gegenüber",
           "gegenuber", "einer", "eines", "über", "uber", "zwischen", "begrenzt", "aktive"},
    "fr": {"le", "la", "les", "des", "du", "pour", "et", "quelles", "quelle", "dans", "entre",
           "jusqu", "simple", "défaut", "defaut", "bail"},
    "it": {"il", "di", "che", "per", "quale", "quali", "della", "nella", "una", "sono", "con",
           "deve", "reatto", "impresa"},
}

_TEXT = {
    "de": {
        "title": "Abdeckung der Anfrage durch den abgerufenen Bestand",
        "model": "Einschätzung des generativen Modells (ohne eigene Zitate, unverändert übernommen):",
        "covered": "Belegte Fundstellen zu « {concept} » ({count} von {total} Entscheidungen):",
        "uncovered": "Nicht belegt im abgerufenen Bestand: {concepts} (je 0 von {total} Entscheidungen).",
        "all": "Alle inhaltlichen Begriffe der Anfrage sind im abgerufenen Bestand belegt.",
        "footnote": ("Zitate sind wörtlich aus den abgerufenen Entscheidungen übernommen; "
                     "die Quelle ist auf der Karte unter der Kennung verlinkt."),
        "reason": "generative_answer_declined_to_cite",
    },
    "fr": {
        "title": "Couverture de la question par le corpus récupéré",
        "model": "Appréciation du modèle génératif (sans citation propre, reprise telle quelle) :",
        "covered": "Fondements cités pour « {concept} » ({count} décisions sur {total}) :",
        "uncovered": "Non couvert par le corpus récupéré : {concepts} (0 décision sur {total} pour chacun).",
        "all": "Tous les notions de la question sont couvertes par le corpus récupéré.",
        "footnote": ("Citations reproduites mot pour mot depuis les décisions récupérées ; "
                     "la source est liée sur la carte sous l'identifiant."),
        "reason": "generative_answer_declined_to_cite",
    },
    "it": {
        "title": "Copertura della questione nel corpus recuperato",
        "model": "Valutazione del modello generativo (senza citazioni proprie, riportata invariata):",
        "covered": "Passaggi citati per « {concept} » ({count} decisioni su {total}):",
        "uncovered": "Non coperto dal corpus recuperato: {concepts} (0 decisioni su {total} per ciascuno).",
        "all": "Tutti i concetti della domanda sono coperti dal corpus recuperato.",
        "footnote": ("Le citazioni sono riportate alla lettera dalle decisioni recuperate; "
                     "la fonte è collegata sulla mappa tramite l'identificativo."),
        "reason": "generative_answer_declined_to_cite",
    },
    "en": {
        "title": "Coverage of the question by the retrieved corpus",
        "model": "Generative model's own assessment (no citations of its own, reproduced unchanged):",
        "covered": "Cited passages for « {concept} » ({count} of {total} decisions):",
        "uncovered": "Not supported by the retrieved corpus: {concepts} (0 of {total} decisions each).",
        "all": "Every content concept of the question is supported by the retrieved corpus.",
        "footnote": ("Quotes are verbatim from the retrieved decisions; each source is linked on "
                     "the map under its identifier."),
        "reason": "generative_answer_declined_to_cite",
    },
}


def detect_language(query: str, decisions: list[dict] | None = None) -> str:
    """Answer in the language the researcher asked in, not the corpus majority."""
    from .concept_coverage import tokenize

    tokens = set(tokenize(query))
    scores = {lang: len(tokens & marks) for lang, marks in _LANG_MARKERS.items()}
    best = max(scores, key=lambda lang: (scores[lang], lang == "de"))
    if scores[best] >= 2:
        return best
    langs = [str(d.get("language") or "") for d in (decisions or [])]
    langs = [l for l in langs if l in ("de", "fr", "it")]
    if langs:
        return max(set(langs), key=langs.count)
    return "en"


def _is_federal(decision: dict) -> bool:
    court = norm(decision.get("court"))
    return court in {"bger", "bge", "bstger", "tribunal federal"} or norm(
        decision.get("decision_id", "")
    ).startswith(("bge ", "bger_", "bge_", "bstger"))


#: Tokens that make a sentence attest a *rule* rather than a fact pattern.  A
#: quote that only names the employer ("der Arbeitgeberin mitteilte …") cites a
#: decision without stating what it decides, which is exactly the kind of
#: citation the gate is meant to expose.
_LEGAL_TOKENS = (
    "pflicht", "art", "abs", "or ", "stgb", "zgb", "cpv", "arbg",
    "gesetz", "regeste", "entscheid", "beschlossen", "festgestellt", "beurteilt",
    "somit", "gemass", "verletzt", "obliegen", "recht", "grundsatz", "unvereinbar",
)

#: A quote that stops mid-sentence ("… (E.") cannot be attested by a reader.
_COMPLETE_RE = re.compile(r"[.;:!?…»\"]\s*$")
#: … but a trailing "E." / "Art." / "Abs." is an abbreviation, not a full stop.
_TRAILING_ABBREV_RE = re.compile(
    r"(?:\b[A-Za-zÀ-ÿ]|\b(?:Art|Abs|Nr|Nrn|Bd|Ziff|S|E|Ss|Kap|Mrz|Ziff))\.\s*$"
)
_EXTEND_RE = re.compile(r"^.{2,80}?[.;:!?…»\"]\s")


def _ends_sentence(text: str) -> bool:
    probe = _TRAILING_ABBREV_RE.sub("", text).rstrip()
    return bool(_COMPLETE_RE.search(probe))


def _complete(sentence: str, raw: str) -> str:
    """Return ``sentence``, extended to its terminator when the split cut early.

    Headnotes and snippets are routinely cut inside a sentence ("… des
    Arbeitgebers (E."). Quoting that fragment would put a truncated proposition
    under a jurist's citation, so the remainder of the sentence is taken from the
    same field of the same row, still verbatim.
    """
    text = sentence.rstrip()
    if _ends_sentence(text):
        return text
    position = raw.find(sentence)
    if position < 0:
        return text
    tail = raw[position + len(sentence): position + len(sentence) + MAX_QUOTE_CHARS]
    stripped = tail.lstrip()
    match = _EXTEND_RE.match(stripped)
    if not match:
        return text
    return (text + " " + stripped[: match.end()].strip()).strip()


def _quote_for(concept: str, decision: dict) -> str | None:
    """Best verbatim sentence of ``decision`` that carries ``concept``.

    Headnotes (``regeste``) are preferred over body text because a headnote is
    the holding, and sentences that state a rule outrank sentences that merely
    narrate the facts.  The sentence is returned unchanged, so "this decision
    says this" stays checkable by string containment.
    """
    prefix = concept_prefix(concept)
    if not prefix:
        return None
    fields = [
        (decision.get("regeste"), 2),          # headnote: the holding
        (decision.get("full_text"), 0),        # body
    ]
    # A snippet is a truncated excerpt ("... weiter").  It is only used when the
    # row carries no text of its own, so a citation never rests on a fragment.
    if not any(decision.get(k) for k in ("regeste", "full_text")):
        fields = [(decision.get("snippet"), 0), (decision.get("title"), 1)]
    best: tuple[int, int, str] | None = None
    for raw, bonus in fields:
        if not raw:
            continue
        text = str(raw)
        for position, sentence in enumerate(_sentences(text)):
            if len(sentence) < MIN_QUOTE_CHARS or len(sentence) > 2400:
                continue
            body = norm(sentence)
            if prefix not in body:
                continue
            legal = sum(1 for token in _LEGAL_TOKENS if token in body)
            score = bonus + min(legal, 3)
            if best is None or score > best[0] or (score == best[0] and position < best[1]):
                best = (score, position, _complete(sentence, text))
        if best is not None and best[0] >= 4:
            break  # a rule-stating headnote sentence: no body text can beat it
    return best[2][:MAX_QUOTE_CHARS] if best else None


def _cited_as(decision: dict) -> str:
    did = str(decision.get("decision_id") or "").strip()
    citation = str(decision.get("citation") or "").strip()
    return f"[{did}] ({citation})" if citation else f"[{did}]"


def ensure_cited_answer(bundle: dict, *,
                        max_concepts: int = MAX_QUOTED_CONCEPTS,
                        max_rows_per_concept: int = MAX_ROWS_PER_CONCEPT) -> dict[str, Any]:
    """Guarantee a sourced answer: cited where the corpus supports it, explicit where it does not.

    Mutates ``bundle["answer"]`` only when the model returned an answer with no
    citations, and always writes ``bundle["provenance"]["answer_gap_contract"]``.
    Returns the report either way, so a caller can see why it did or did not run.
    """
    answer = bundle.get("answer") or {}
    decisions = [d for d in (bundle.get("decisions") or []) if isinstance(d, dict)]
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "fired": False,
        "reason": None,
        "coverage": {},
        "quotes": [],
        "cited_decision_ids": [],
        "under_covered": [],
        "claim_ceiling": (
            "verbatim quotes from decisions already in this bundle, grouped by the query concepts "
            "the retrieved corpus covers; the uncovered list is a lexical coverage measurement of "
            "the retrieved set, not a statement about the whole corpus of Swiss case law"
        ),
    }

    if str(answer.get("status") or "") not in ("ready", "degraded"):
        report["reason"] = f"answer status {answer.get('status')!r} is not a surfaced answer"
        _record(bundle, report)
        return report
    already = [str(x) for x in (answer.get("cited_decision_ids") or [])]
    if already:
        report["reason"] = "answer already cites retrieved decisions"
        report["cited_decision_ids"] = already
        _record(bundle, report)
        return report

    query = str(bundle.get("query") or "")
    # One normalisation pass per row, shared by the coverage report and the
    # per-concept row lookup: the whole contract must stay far below the
    # local map budget, and full texts run to tens of kB per row.
    texts = {str(d.get("decision_id")): decision_text(d) for d in decisions}
    coverage = coverage_report(query, decisions, texts=texts)
    report["coverage"] = {k: coverage[k] for k in
                          ("concepts", "rows_per_concept", "covered", "under_covered",
                           "n_decisions", "n_decisions_with_text")}
    report["under_covered"] = list(coverage["under_covered"])
    if not coverage["concepts"]:
        report["reason"] = "the question has no content concept to report coverage for"
        _record(bundle, report)
        return report

    covered = sorted(coverage["covered"], key=lambda c: (-coverage["rows_per_concept"][c], c))
    blocks: list[dict[str, Any]] = []
    statements: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_quotes: set[str] = set()
    for concept in covered[:max_concepts]:
        picked: list[dict[str, Any]] = []
        candidates = rows_for_concept(concept, decisions, limit=max_rows_per_concept * 4,
                                     texts=texts)
        # Federal practice (BGE/BGer) states the rule; cantonal decisions apply
        # it.  For an answer whose job is to say what the corpus holds, the
        # leading authority comes first, deterministically.
        candidates.sort(key=lambda d: (0 if _is_federal(d) else 1,
                                       int(d.get("rank") or 10**9),
                                       str(d.get("decision_id") or "")))
        for decision in candidates:
            if len(picked) >= max_rows_per_concept:
                break
            quote = _quote_for(concept, decision)
            if not quote:
                continue
            did = str(decision.get("decision_id") or "")
            if not did or did in seen_ids:
                continue
            key = norm(quote)[:160]
            if key in seen_quotes:
                # The same sentence already carries an earlier concept; a second
                # copy of it would pad the answer without adding authority.
                continue
            seen_quotes.add(key)
            seen_ids.add(did)
            entry = {
                "concept": concept,
                "decision_id": did,
                "rank": decision.get("rank"),
                "court": decision.get("court"),
                "language": decision.get("language"),
                "citation": decision.get("citation"),
                "quote": quote,
                "cited_as": _cited_as(decision),
                "rows_for_concept": coverage["rows_per_concept"][concept],
            }
            picked.append(entry)
            statements.append({
                "text": quote,
                "decision_id": did,
                "concept": concept,
                "relevance": round(1.0 / (1.0 + int(decision.get("rank") or 10**4) / 100.0), 4),
            })
        if picked:
            blocks.append({"concept": concept, "count": coverage["rows_per_concept"][concept],
                           "entries": picked})

    report["quotes"] = [e for b in blocks for e in b["entries"]]
    if not blocks:
        # Nothing quotable: leave the answer exactly as the model wrote it. The
        # gate-admissibility check then blocks the question, which is the honest
        # outcome - a citation would have to be invented.
        report["reason"] = "no retrieved decision states a concept of the question"
        _record(bundle, report)
        return report

    lang = detect_language(query, decisions)
    text = _TEXT.get(lang, _TEXT["en"])
    total = coverage["n_decisions"] or 0
    lines: list[str] = [text["title"], ""]
    model_prose = str(answer.get("prose") or "").strip()
    if model_prose:
        lines += [text["model"], model_prose, ""]
    for block in blocks:
        lines.append(text["covered"].format(concept=block["concept"], count=block["count"], total=total))
        for entry in block["entries"]:
            lines.append(f"« {entry['quote']} » {entry['cited_as']}")
        lines.append("")
    if coverage["under_covered"]:
        lines.append(text["uncovered"].format(
            concepts=", ".join(f"«{c}»" for c in coverage["under_covered"]), total=total))
    else:
        lines.append(text["all"])
    lines += ["", text["footnote"]]

    out = copy.deepcopy(answer)
    out["prose"] = "\n".join(lines).strip()
    out["statements"] = statements
    out["cited_decision_ids"] = sorted(seen_ids)
    out["status"] = "degraded"
    out["method"] = "concept_coverage_extractive_v1"
    out["gap_reason"] = text["reason"]
    out["coverage"] = {
        "concepts": coverage["concepts"],
        "rows_per_concept": coverage["rows_per_concept"],
        "covered": coverage["covered"],
        "under_covered": coverage["under_covered"],
    }
    if model_prose:
        out["superseded_prose"] = model_prose
        out["superseded_method"] = answer.get("method")
    bundle["answer"] = out

    report.update({
        "fired": True,
        "reason": text["reason"],
        "language": lang,
        "n_quotes": len(statements),
        "quoted_concepts": [b["concept"] for b in blocks],
        "cited_decision_ids": out["cited_decision_ids"],
        "answer_status": out["status"],
        "answer_method": out["method"],
    })
    _record(bundle, report)
    return report


def _record(bundle: dict, report: dict[str, Any]) -> None:
    prov = bundle.setdefault("provenance", {})
    existing = prov.get("answer_gap_contract")
    if isinstance(existing, dict) and existing.get("fired"):
        return  # never downgrade an applied contract with a later no-op pass
    prov["answer_gap_contract"] = report


__all__ = ["SCHEMA", "MAX_QUOTED_CONCEPTS", "MAX_ROWS_PER_CONCEPT", "detect_language",
           "ensure_cited_answer"]
