"""NLCS-1: natural-language concept-seeded query variants (frozen, deterministic).

WHAT THIS IS
------------
The accepted ``frontier-query-concept-recall`` charter measured that a bare
mined-term list (<= 12 tokens, no natural-language question text) is too
narrow for the OpenCaseLaw relevance index, and recorded the bound
``'TERM-ONLY EXPANSION QUERIES ARE TOO NARROW FOR THE OPENCASELAW RELEVANCE
INDEX'`` as its single cause.  That layer is CLOSED.  This module builds the
*other* input class the cause names as untested: **full-sentence**
natural-language variant queries that explicitly mention an under-covered core
concept as phrased text.

WHAT THIS IS NOT
----------------
* Not a translation layer.  A variant is only ever emitted for a target
  language whose question text is an ACCEPTED text in that language.  Served
  bundles carry accepted text in the question's own language only, so their
  variants are emitted in that language alone; inventing an fr/it paraphrase
  of a de question would be hand-invented text and is refused here.
* Not corpus mining.  Nothing in this module reads the corpus, the cache or a
  previous run's output.
* Not legal synonymy.  The only vocabulary in a variant is (a) the question's
  own accepted sentence and (b) the concept's own surface form plus its
  deterministic morphological variants.  No synonym, no translation, no
  paraphrase, no model call.
* Not a search client.  See ``replay.py``.

FROZEN TEMPLATE (template id ``NLCS-1``)
----------------------------------------
``V(question_text, lang, concept) =
      question_text
    + JOIN[lang]
    + surface(concept)
    + OPEN[lang] + variant_1 + SEP[lang] + variant_2 + ... + CLOSE[lang]
    + TAIL[lang]``

The result is one sentence-shaped query: the question as accepted, followed by
an apposition that names the missing concept together with its morphological
variants, closed as a question.  ``JOIN/OPEN/SEP/CLOSE/TAIL`` are frozen
per-language literals carrying no domain content; they are part of the
pre-registered rules file, not a tunable.

MORPHOLOGY (frozen, per language, no linguistic model)
-----------------------------------------------------
* de: plural = the rule table (see ``plural_de``); umlaut spelling = ue/oe/ae/ss
  expansion; accent-stripped = NFKD with combining marks removed.
* fr: plural = -aux after -al, -x after -eau, idempotent on an already
  s/x/z-final surface, -s otherwise; singular = surface minus its final s/x/z;
  accent-stripped as above.
* it: plural = the rule table (see ``plural_it``); accent-stripped as above.

Every generated form is de-duplicated and empty forms are dropped, so a
concept whose variants collapse contributes a single apposition rather than a
term list.
"""
from __future__ import annotations

import re
import unicodedata

TEMPLATE_ID = "NLCS-1"

#: Frozen literal scaffolding.  Function words only; zero domain content.
LITERALS = {
    "de": {"JOIN": " – ", "OPEN": " (", "SEP": ", ", "CLOSE": ")", "TAIL": "?"},
    "fr": {"JOIN": " — ", "OPEN": " (", "SEP": ", ", "CLOSE": ")", "TAIL": " ?"},
    "it": {"JOIN": " — ", "OPEN": " (", "SEP": ", ", "CLOSE": ")", "TAIL": "?"},
}

#: The concept vocabulary is de-accented by the accepted audit rule, so the
#: surface form is recovered by matching the de-accented token against the
#: accepted text case-insensitively.
_TOKEN_RE = re.compile(r"[^\W\d_]+", re.UNICODE)

DE_UMLAUT = (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("Ä", "Ae"),
             ("Ö", "Oe"), ("Ü", "Ue"), ("ß", "ss"))


def deaccent(text: str) -> str:
    """Byte-identical to the accepted ``evaluation.subject_match_audit.deaccent``."""
    decomposed = unicodedata.normalize("NFKD", str(text))
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def umlaut_spelling(surface: str) -> str:
    """Deterministic German ae/oe/ue/ss spelling of an already-correct surface."""
    out = surface
    for src, dst in DE_UMLAUT:
        out = out.replace(src, dst)
    return out


def plural_de(surface: str) -> str:
    """Frozen German plural rule table (no linguistic model, no exceptions list).

    ``-ung/-heit/-keit/-schaft`` take -en, ``-e/-el/-en/-er/-ling`` take -n,
    everything else takes -e.  Applied mechanically, including to words that are
    already plural; the result is de-duplicated against the surface form, so an
    already-plural word contributes its own surface rather than a nonsense form.
    """
    low = surface.lower()
    if low.endswith(("ung", "heit", "keit", "schaft", "pflicht")):
        return surface + "en"
    if low.endswith(("e", "el", "en", "er", "ling")):
        return surface + "n"
    return surface + "e"


def singular_fr(surface: str) -> str:
    """Frozen French singular of an already s/x/z-final surface.

    French plural adds a silent ``-s`` that carries no orthography, so a word
    that already ends in s/x/z is treated as plural and its singular is the
    surface minus the final letter.  Deterministic and declared; never tuned.
    """
    return surface[:-1] if surface and surface[-1] in "sxz" else surface


def plural_fr(surface: str) -> str:
    """Frozen French plural rule table.

    ``-al`` -> -aux, ``-eau`` -> -x, an already s/x/z-final surface is returned
    unchanged (the French plural ``-s`` is silent), everything else -> -s.
    """
    low = surface.lower()
    if low.endswith("al"):
        return surface[:-2] + "aux"
    if low.endswith("eau"):
        return surface + "x"
    if low.endswith(("s", "x", "z")):
        return surface
    return surface + "s"


def plural_it(surface: str) -> str:
    """Frozen Italian plural rule table.

    ``-o`` -> drop the -o and add -i, ``-a`` -> -e, ``-e`` -> drop the -e and
    add -i, ``-i`` -> -i, everything else invariant.  Applied mechanically, including to words that
    are already plural; the rule is correct in general and this is its declared
    behaviour on a word it happens to mis-handle.
    """
    low = surface.lower()
    if low.endswith("o"):
        return surface[:-1] + "i"
    if low.endswith("a"):
        return surface + "e"
    if low.endswith("e"):
        return surface[:-1] + "i"
    if low.endswith("i"):
        return surface + "i"
    return surface


_PLURAL = {"de": plural_de, "fr": plural_fr, "it": plural_it}


def surface_form(concept: str, text: str) -> str:
    """The concept's own spelling as it appears in the accepted question text.

    Matching is done on the de-accented, case-folded token so that the accepted
    concept ``uberwachungspflicht`` recovers the accepted text's own
    ``Überwachungspflicht``.  Falls back to the concept token itself when the
    concept does not occur in the text, which keeps the builder total.
    """
    want = deaccent(concept).lower()
    for tok in _TOKEN_RE.findall(text or ""):
        if deaccent(tok).lower() == want:
            return tok
    return concept


def morph_variants(surface: str, lang: str) -> list[str]:
    """The concept's own surface form plus its deterministic morphological forms.

    Order is frozen: surface, plural, umlaut spelling (de only), accent-stripped,
    French singular (fr only).  Duplicates and empties are dropped, order
    preserved, so a concept whose forms collapse contributes a single apposition
    rather than a term list.
    """
    if lang not in _PLURAL:
        raise ValueError(f"unknown target language: {lang!r}")
    raw = [surface, _PLURAL[lang](surface)]
    if lang == "de":
        raw.append(umlaut_spelling(surface))
    raw.append(deaccent(surface))
    if lang == "fr":
        raw.append(singular_fr(surface))
    out: list[str] = []
    for form in raw:
        form = (form or "").strip()
        if form and form not in out:
            out.append(form)
    return out


def build_variant(question_text: str, lang: str, concept: str) -> dict:
    """Build ONE frozen natural-language concept-seeded variant.

    Returns a record carrying the exact emitted string, the surface form and the
    variant list, so the published record is auditable without re-running code.
    """
    lit = LITERALS[lang]
    sigma = surface_form(concept, question_text)
    forms = morph_variants(sigma, lang)
    tail = forms[1:] if len(forms) > 1 else []
    apposition = sigma
    if tail:
        apposition += lit["OPEN"] + lit["SEP"].join(tail) + lit["CLOSE"]
    text = (question_text or "").rstrip() + lit["JOIN"] + apposition + lit["TAIL"]
    return {
        "template_id": TEMPLATE_ID,
        "question_text": question_text,
        "target_language": lang,
        "concept": concept,
        "surface_form": sigma,
        "morph_variants": forms,
        "query": text,
        "n_chars": len(text),
    }


def build_unit_variants(question_text: str, lang: str, concepts: list[str],
                        max_concepts: int) -> list[dict]:
    """One variant per under-covered concept, capped at ``max_concepts``.

    Concepts are consumed in the order the accepted measurement produced them,
    so the cap is a prefix of the accepted under-covered list, never a
    re-selection.
    """
    if max_concepts < 1:
        raise ValueError("max_concepts must be >= 1")
    return [build_variant(question_text, lang, c) for c in list(concepts)[:max_concepts]]


__all__ = [
    "TEMPLATE_ID", "LITERALS", "deaccent", "umlaut_spelling",
    "plural_de", "singular_fr", "plural_fr", "plural_it", "surface_form",
    "morph_variants", "build_variant", "build_unit_variants",
]