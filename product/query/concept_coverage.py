"""Does the retrieved result set actually cover *every* concept of the question?

Why this exists
---------------
The multi-query human-gate packet of direction v52 backlog item (3) shipped three
pre-registered research questions and blocked one of them.  The blocking finding
was ``answer_cites_nothing`` on ``de-kapitalverletzung`` ("Aktive
Fürsorgepflicht des Arbeitgebers bei einer Kapitalverletzung …").  The obvious
reading was "the answer generator forgot to cite"; the previous cycle recorded
that as the hypothesis.

Reading the shipped bundle shows the opposite.  The bundle (134 decisions)
contains 23 rows on the employer's *Fürsorgepflicht* and **0 rows** on
*Kapitalverletzung*.  The generative model therefore did not forget to cite: it
read 30 sources that cover one concept of a two-concept question and correctly
refused to present the other concept's authority as an answer.  Six live
OpenCaseLaw probes (``product/reports``: "Fürsorgepflicht Arbeitgeber
Insolvenz Konkurs" total 72, "Arbeitgeber Schutzpflicht Kapitalverletzung OR
328" total 115, …) confirm the split: the employer's duty of care is a real
Swiss line (BGE 132 III 257, BGE 132 III 115, BGE 4A 611/2018), while the
capital-impairment combination has no on-point decision in the corpus.

A product that hides that is worse than one that red-lines: the researcher must
be able to see *which part* of the question the corpus covers and which part it
does not, and must get citations for the part that is covered.

This module provides the measurement, deterministically and offline:

* :func:`content_concepts` - the content concepts of a DE/FR/IT question
  (function words, statute abbreviations and interrogatives removed, order
  preserved);
* :func:`coverage_report` - per concept: how many retrieved decisions actually
  carry it, and which concepts are under-covered;
* :func:`rows_for_concept` - the highest-ranked decisions that carry a concept,
  used to cite the covered part and to name what is missing.

Matching is a normalised (NFKD, de-accented, casefolded) prefix match, which is
a cheap but honest approximation for German compounds: ``kapitalverletzung``
also matches ``Kapitalverletzungen`` and ``Kapitalverlust``, ``fürsorgepflicht``
matches ``Fürsorgepflichten``.  Nothing here is learned, sampled or model
dependent: the same bundle always yields the same report.

Usage
-----
    python -m product.query.concept_coverage "Aktive Fürsorgepflicht …"
    from product.query.concept_coverage import coverage_report
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Iterable

#: A concept shorter than this is noise ("wie", "was", "bis", "bei").
MIN_CONCEPT_CHARS = 5

#: Minimum prefix length used for compound-aware matching.
MIN_PREFIX_CHARS = 6

#: A concept needs at least this many retrieved rows before the product calls it
#: covered.  One incidental mention in a hundred decisions is not coverage.
MIN_ROWS_PER_CONCEPT = 2

#: Bound on how many concepts one answer/report may address (long questions are
#: decomposed into their leading concepts, deterministically).
MAX_CONCEPTS = 8

TOKEN_RE = re.compile(r"[^\W\d_]+", re.UNICODE)

#: Function words, statute abbreviations and legal-form tokens in DE/FR/IT/EN.
#: The first entries are the ones observed as junk cluster labels on accepted
#: bundles ("abs, in, stpo, iv, sein"), which is how a concept list turns into
#: the same junk if it is not filtered.
STOPWORDS = frozenset(
    """
    abs abt allg als also amt ander andere anderem anderen anderer anderes anfang
    antwort arbeit arbeiten arbeitgeber arbeitnehmer art artikel auf aus ausser
    beanstandet bedarf beginn bereits besagt besonders bestehen betreffend
    betrifft bzw dabei dach daruber darum das dass davon demselben den denen der
    deren des deshalb dessen deutsch dienst die dies diese diesem diesen dieser
    dieses doch dort du durch eine einem einen einer eines einige enthaelt
    enthalt er es etwa etwas euch fall fur ganz gegen gegenuber geheut gilt
    grund halte haben hat hatte hatten hauptteil heute hier hin hinter hoch
    insbesondere ist ja jede jedem jeden jeder jedes jene jener jetzt kann kann
    kein keine keinem keinen keiner keines kommen konnte kunft kurz lang
    laufe laufen leicht machen macht mal man mehr mein meine mit moeglich
    moeglichkeit muss musste nach nachdem nein neu nicht nichts noch nun nur ob
    obwohl oder ohne ober publikation recht regel richten richtlinie sache sagt
    samt schlecht schon see siehe somit sondern sonst sowie sowohl stgb stpo
    str text tier urteil urteile veroeffentlicht viel viele vorn waehrend wann
    warum wegen weiter weitere welche welchem welchen welcher welches wenn wer
    werde werden wessen wie wieder wir wird wirt wort zeit ziff
    ainsi alors aucun autre autres aux avec avoir ayant car cela ces cet cette
    ceux chaque comme comment dans des deux doit donc dont elle elles en encore
    entre est etre etaient etait etant etc etre eux fait faire fois font hors
    ici il ils jamais jusqu leur leurs lorsque lui mais meme mes moi moins mon
    nos notre nous par parce parmi pas pendant peu peut plus plusieurs pour
    pourquoi pourtant qu quand que quel quelle quelles quels qui quoi sa sans se
    selon sera serait ses seulement si sien soit sommes son sont sous soyez suis
    sur tant tes toi ton toujours tous tout toute toutes tres trop une vers vos
    votre vous y
    affermi all art colui come con cui dei del della delle della dei degli dei
    della dove due e ed egli ella essa essere fa fino fra gli grande ha hanno
    ho i il in io la le lei li lo loro ma me mentre mio molto ne negli nei nel
    nella nelle negli noi non nostra nostro o ogni per perche pero piu poco poi
    puo quale quanta quante quanti quanto quel quella quelle quello questa
    queste questi questo quindi se sei senza si sia siamo solo sono sopra sotto
    sta stato su sua sue sugli sui sul sulla sulle suo suoi tra tre troppo tu tua
    tuo tutti tutto un una uno voi vostro
    criterio criteri criterio criteres criteres grundsatz grundsaetze dottrina
    dottrina doctrine fall faelle fallfrage frage question questions
    entscheid entscheidung entscheidungen entscheide entscheidet
    unterscheidet unterscheidung unterscheidungen begrenzt begrenzen
    begrenzung begrenzungen entscheidungs praxis jurisprudence
    bloss blosse blossen geht gehts gilt haeufig haufig
    fuehrt fuehren fuehrte fuehrung fuehrungen fuehrungs
    resiliation orient orientierung orientations
    and any are as at be been being but by can could did do does doing for from
    had has have how i if in into is it its may might more most must no nor not
    of off on once only or other others our out over own same shall should so
    some such than that the their them then there these they this those through
    to too under until up very was we were what when where which while who why
    will with would you your
    """.split()
)


def norm(value: Any) -> str:
    """NFKD, strip combining marks, casefold, collapse whitespace.

    Byte-identical to ``product/query/answer_contract.py::norm`` so coverage
    detection and the answer-completeness contracts cannot disagree about what
    a word is.
    """
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.casefold().split())


def tokenize(text: str) -> list[str]:
    return [t.casefold() for t in TOKEN_RE.findall(text or "")]


def content_concepts(query: str, *, limit: int = MAX_CONCEPTS) -> list[str]:
    """Ordered, de-duplicated content concepts of a research question.

    Order is the order of appearance, which keeps the report stable and makes
    the leading concepts of a question the ones reported when ``limit`` bites.
    """
    out: list[str] = []
    for raw in tokenize(query):
        token = "".join(ch for ch in unicodedata.normalize("NFKD", raw)
                        if not unicodedata.combining(ch))
        if len(token) < MIN_CONCEPT_CHARS or token in STOPWORDS:
            continue
        if token not in out:
            out.append(token)
        if len(out) >= limit:
            break
    return out


def concept_prefix(concept: str) -> str:
    """The prefix used to match a concept inside normalised decision text."""
    return concept[: max(MIN_PREFIX_CHARS, len(concept) - 4)]


def matches_concept(normalised_text: str, concept: str) -> bool:
    prefix = concept_prefix(concept)
    return bool(prefix) and prefix in normalised_text


def decision_text(decision: dict) -> str:
    """Everything the product already holds for a row, normalised.

    Citation-channel shells have no text of their own; they are skipped by
    counting rows with text, which is the honest denominator.
    """
    parts = [
        decision.get("full_text"),
        decision.get("regeste"),
        decision.get("snippet"),
        decision.get("title"),
    ]
    return norm(" \n ".join(str(p) for p in parts if p))


def coverage_report(query: str, decisions: Iterable[dict], *,
                    min_rows: int = MIN_ROWS_PER_CONCEPT,
                    texts: dict[str, str] | None = None) -> dict[str, Any]:
    """Per-concept coverage of the retrieved set, recomputed from the bundle.

    ``texts`` may carry pre-normalised row texts (keyed by ``decision_id``) so a
    caller that needs both this report and :func:`rows_for_concept` normalises
    each row once instead of once per concept.
    """
    rows = [d for d in (decisions or []) if isinstance(d, dict)]
    if texts is None:
        texts = {str(d.get("decision_id")): decision_text(d) for d in rows}
    with_text = [d for d in rows if texts.get(str(d.get("decision_id")))]
    n = len(rows)
    concepts = content_concepts(query)
    values = list(texts.values())
    counts: dict[str, int] = {}
    for concept in concepts:
        prefix = concept_prefix(concept)
        counts[concept] = sum(1 for t in values if prefix and prefix in t)
    covered = [c for c in concepts if counts.get(c, 0) >= min_rows]
    under = [c for c in concepts if c not in covered]
    return {
        "method": "query_concept_coverage_v1",
        "n_decisions": n,
        "n_decisions_with_text": len(with_text),
        "concepts": concepts,
        "rows_per_concept": counts,
        "shares": {c: round(counts[c] / n, 4) if n else 0.0 for c in concepts},
        "min_rows_per_concept": min_rows,
        "covered": covered,
        "under_covered": under,
        "all_covered": bool(concepts) and not under,
        "note": (
            "row counts are lexical coverage of the retrieved set, not a legal conclusion: "
            "a concept can be covered by rows that are on point and by rows that only name it"
        ),
    }


def rows_for_concept(concept: str, decisions: Iterable[dict], *, limit: int = 5,
                     texts: dict[str, str] | None = None) -> list[dict]:
    """Highest-ranked decisions whose own text carries ``concept``."""
    prefix = concept_prefix(concept)
    if not prefix:
        return []
    rows = [d for d in (decisions or []) if isinstance(d, dict)]
    rows.sort(key=lambda d: (int(d.get("rank") or 10**9), str(d.get("decision_id") or "")))
    if texts is None:
        texts = {str(d.get("decision_id")): decision_text(d) for d in rows}
    out = [d for d in rows if prefix in texts.get(str(d.get("decision_id")), "")]
    return out[:limit]


__all__ = [
    "MIN_CONCEPT_CHARS", "MIN_ROWS_PER_CONCEPT", "MAX_CONCEPTS", "STOPWORDS",
    "norm", "tokenize", "content_concepts", "concept_prefix", "matches_concept",
    "decision_text", "coverage_report", "rows_for_concept",
]
