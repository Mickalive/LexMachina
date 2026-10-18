"""Deterministic, corpus-derived, multilingual query-expansion layer.

Drop-in behind the existing bundle seam: it emits ONE extra query variant per
(question, target language) and one additive ``provenance.query_expansion``
object.  It does not touch the retrieval adapter, the cache, pagination,
normalisation, dedup, the classifier, the geometry or the layout, and it issues
no counter-authority label.

Determinism
-----------
Every function here is a pure function of (corpus sample, question text,
language).  No randomness, no model call, no network.  The same inputs always
produce the same terms, in the same order.

Corpus derivation
-----------------
Terms are mined from the read-only corpus sample (served bundle rows + the
accepted benchmark record's embedded cached rows) with a plain conditional
document-frequency ratio, per target language.  Nothing is hand-typed per
question: the accepted product ``EXPANSION`` lexicon is consulted only as an
additional exact-token synonym source, exactly as the product already does.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Iterable

TOKEN_RE = re.compile(r"[^\W\d_]+", re.UNICODE)

#: Frozen parameters (see RULES.json).  Changing any of these is a threshold
#: edit and invalidates a run that has already seen a number.
N_TERMS_PER_CONCEPT = 4
MAX_QUERY_TERMS = 12
MIN_TERM_CHARS = 5
#: A mined term must be carried by at least this many documents of the target
#: language, otherwise it is corpus noise rather than corpus vocabulary.
MIN_TERM_DF = 2

LANGUAGES = ("de", "fr", "it")

#: Frozen head-noun suffixes per language, longest-first at match time.
SUFFIXES: dict[str, tuple[str, ...]] = {
    "de": (
        "lichkeit", "schaft", "keit", "heit", "ung", "nis", "tion", "ität",
        "anz", "enz", "ent", "tum", "ler", "bar", "sam", "haft", "los",
        "reich", "voll", "ig", "lich", "isch", "end", "ern", "ung",
    ),
    "fr": (
        "isation", "isation", "issement", "ement", "ation", "ance", "ence",
        "ité", "ette", "age", "eur", "euse", "ier", "ière", "al",
    ),
    "it": (
        "izzazione", "azione", "imento", "anza", "enza", "ità", "aggio",
        "ismo", "ista", "abile", "ivo", "ale",
    ),
}


def norm(value: Any) -> str:
    """NFKD, strip combining marks, casefold, collapse whitespace.

    Byte-identical to the accepted ``concept_coverage.norm`` so the mined
    lexicon and the coverage metric can never disagree about what a word is.
    """
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.casefold().split())


def tokens(text: str) -> list[str]:
    return TOKEN_RE.findall(norm(text))


# --------------------------------------------------------------------------- #
# Corpus sample
# --------------------------------------------------------------------------- #
@dataclass
class CorpusSample:
    """Per-language document frequency over the read-only corpus sample."""

    stoplist: frozenset[str]
    docs: dict[str, list[frozenset[str]]] = field(default_factory=dict)
    joined: dict[str, list[str]] = field(default_factory=dict)
    n_rows: dict[str, int] = field(default_factory=dict)

    @classmethod
    def build(cls, *, stoplist: Iterable[str], bundle_rows: Iterable[dict],
              benchmark_rows: Iterable[dict]) -> "CorpusSample":
        stop = frozenset(stoplist)
        raw: dict[str, list[str]] = {lang: [] for lang in LANGUAGES}
        counts: dict[str, int] = {lang: 0 for lang in LANGUAGES}

        for row in bundle_rows:
            lang = str(row.get("language") or "").lower()
            if lang not in raw:
                continue
            text = " \n ".join(str(row.get(field) or "") for field in (
                "regeste", "title", "snippet", "citation", "docket_number"))
            raw[lang].append(text)
            counts[lang] += 1

        for row in benchmark_rows:
            lang = str(row.get("language") or "").lower()
            if lang not in raw:
                continue
            text = " \n ".join(str(row.get(field) or "") for field in (
                "text_head", "citation_string_de", "citation_string_fr",
                "citation_string_it", "docket_number"))
            raw[lang].append(text)
            counts[lang] += 1

        docs: dict[str, list[frozenset[str]]] = {}
        joined: dict[str, list[str]] = {}
        for lang, texts in raw.items():
            out: list[frozenset[str]] = []
            flat: list[str] = []
            for text in texts:
                toks = frozenset(
                    t for t in tokens(text)
                    if len(t) >= MIN_TERM_CHARS and t.isalpha() and t not in stop
                )
                if toks:
                    out.append(toks)
                    flat.append(" ".join(sorted(toks)))
            docs[lang] = out
            joined[lang] = flat
        return cls(stoplist=stop, docs=docs, joined=joined, n_rows=counts)

    # -- mining ----------------------------------------------------------- #
    def df(self, token: str, language: str) -> int:
        return sum(1 for doc in self.docs.get(language) or [] if token in doc)

    def vocabulary(self, language: str, *, min_df: int = 1) -> frozenset[str]:
        """Tokens that actually occur in this language's corpus sample."""
        counts: dict[str, int] = {}
        for doc in self.docs.get(language) or []:
            for tok in doc:
                counts[tok] = counts.get(tok, 0) + 1
        return frozenset(t for t, n in counts.items() if n >= min_df)

    def mine(self, concept_prefix: str, language: str, *,
             limit: int = N_TERMS_PER_CONCEPT) -> list[tuple[str, float]]:
        """Top-``limit`` terms associated with ``concept_prefix`` in ``language``.

        Score is the conditional document frequency ratio
        ``df(t | concept) / df(t)``: a term that co-occurs with the concept far
        more often than chance, i.e. the corpus's own vocabulary for the
        concept rather than a hand-written translation.

        Three authoring constraints keep the output well-formed:

        * ``df_L(t) >= MIN_TERM_DF (2)`` - a term the corpus barely uses cannot
          carry a doctrinal association;
        * ``t`` is not morphologically the concept itself (``concept_prefix in t``
          or ``t in concept_prefix``), so ``arbeitgeberseitig`` is not offered as
          an expansion of ``arbeitgebers``;
        * ties on score are broken by corpus support DESCENDING then token
          ascending.  Breaking ties alphabetically instead selects the
          alphabetically-first noise word, which is a generator defect, not a
          finding.
        """
        docs = self.docs.get(language) or []
        flats = self.joined.get(language) or []
        if not docs or not concept_prefix:
            return []
        holders = [d for d, flat in zip(docs, flats) if concept_prefix in flat]
        if not holders:
            return []
        n_cond = len(holders)
        cond_counts: dict[str, int] = {}
        for doc in holders:
            for tok in doc:
                cond_counts[tok] = cond_counts.get(tok, 0) + 1
        df: dict[str, int] = {}
        for doc in docs:
            for tok in doc:
                df[tok] = df.get(tok, 0) + 1
        scored: list[tuple[str, float, int]] = []
        for tok, c in cond_counts.items():
            if tok in self.stoplist or len(tok) < MIN_TERM_CHARS or not tok.isalpha():
                continue
            if concept_prefix in tok or tok in concept_prefix:
                continue
            total = df.get(tok, 0)
            if total < MIN_TERM_DF:
                continue
            scored.append((tok, c / total, total))
        # Deterministic: score desc, corpus support desc, token ascending.
        scored.sort(key=lambda t: (-round(t[1], 6), -t[2], t[0]))
        return [(t, s) for t, s, _ in scored[:limit]]

    def summary(self) -> dict[str, Any]:
        return {
            "documents_per_language": {k: len(v) for k, v in self.docs.items()},
            "rows_per_language": dict(self.n_rows),
            "token_stoplist_size": len(self.stoplist),
        }


# --------------------------------------------------------------------------- #
# Compound decomposition
# --------------------------------------------------------------------------- #
def compound_stems(concept: str, language: str,
                    vocabulary: frozenset[str] | None = None) -> list[str]:
    """Deterministic head/modifier stem split of a German/French/Italian compound.

    Strips the longest matching frozen head-noun suffix and keeps the resulting
    head stem plus the modifier prefix, dropping anything shorter than
    ``MIN_TERM_CHARS``.

    When a corpus vocabulary is supplied, a stem is kept **only if the corpus
    actually uses it**.  Without that guard the splitter emits truncated
    pseudo-words (``kapitalverletz``, ``resili``, ``baill``) that match nothing;
    emitting a string the corpus never contains is a generator defect, not a
    lexical finding.
    """
    out: list[str] = []
    for suffix in sorted(SUFFIXES.get(language, ()), key=len, reverse=True):
        if concept.endswith(suffix) and len(concept) - len(suffix) >= MIN_TERM_CHARS:
            head = concept[: len(concept) - len(suffix)]
            out.append(head)
            if head != concept:
                out.append(suffix)
            break
    stems = [t for t in out if len(t) >= MIN_TERM_CHARS]
    if vocabulary is not None:
        stems = [t for t in stems if t in vocabulary]
    return stems


# --------------------------------------------------------------------------- #
# The layer
# --------------------------------------------------------------------------- #
@dataclass
class Expansion:
    language: str
    query: str
    terms: list[str]
    concepts: list[str]
    per_concept: dict[str, dict[str, Any]]
    lexicon_synonyms: list[str]

    def provenance(self) -> dict[str, Any]:
        return {
            "layer": "frontier-query-concept-recall/concept_recall_expansion_v1",
            "deterministic": True,
            "corpus_derived": True,
            "model_calls": 0,
            "network_calls": 0,
            "target_language": self.language,
            "concepts": list(self.concepts),
            "terms": list(self.terms),
            "n_terms": len(self.terms),
            "per_concept": self.per_concept,
            "accepted_lexicon_synonyms": list(self.lexicon_synonyms),
            "note": (
                "additive query variants only; no decision is removed, re-ranked "
                "out of existence or labelled by this layer"
            ),
        }


def build_expansion(question: str, language: str, sample: CorpusSample, *,
                    concept_prefix_fn, content_concepts_fn,
                    accepted_lexicon: dict[str, list[str]] | None = None,
                    shuffle_terms: list[str] | None = None,
                    blank: bool = False) -> Expansion:
    """Build the one expansion query for ``(question, language)``.

    ``blank=True`` produces the frozen A2 control (empty term set).
    ``shuffle_terms`` carries the frozen A3 control (another question's terms).
    """
    concepts = list(content_concepts_fn(question))

    if blank:
        return Expansion(language, "", [], concepts, {}, [])

    if shuffle_terms is not None:
        return Expansion(language, " ".join(shuffle_terms), list(shuffle_terms),
                         concepts, {"shuffled_control": {"terms": list(shuffle_terms)}}, [])

    accepted = dict(accepted_lexicon or {})
    ordered: list[str] = []
    per_concept: dict[str, dict[str, Any]] = {}
    lexicon_synonyms: list[str] = []

    def add(term: str) -> None:
        if term and term not in ordered:
            ordered.append(term)

    question_tokens = set(tokens(question))
    for concept in concepts:
        prefix = concept_prefix_fn(concept)
        mined = sample.mine(prefix, language)
        stems = compound_stems(concept, language, sample.vocabulary(language))
        synonyms: list[str] = []
        for tok in tokens(concept):
            for syn in accepted.get(tok, []):
                if syn not in question_tokens and syn not in synonyms:
                    synonyms.append(syn)
        lexicon_synonyms.extend(synonyms)
        per_concept[concept] = {
            "prefix": prefix,
            "mined": [t for t, _ in mined],
            "mined_scores": {t: round(s, 6) for t, s in mined},
            "stems": stems,
            "accepted_lexicon_synonyms": synonyms,
        }
        # Order: exact accepted synonyms, then mined corpus vocabulary, then stems.
        for term in [*synonyms, *[t for t, _ in mined], *stems]:
            add(norm(term))

    terms = ordered[:MAX_QUERY_TERMS]
    return Expansion(language, " ".join(terms), terms, concepts, per_concept,
                     sorted(set(lexicon_synonyms)))


def blanked(expansion: Expansion) -> Expansion:
    """A2: the same algorithm with an empty term set."""
    return Expansion(expansion.language, "", [], expansion.concepts, {}, [])


def shuffled(source: Expansion) -> Expansion:
    """A3: another question's term set, used on the wrong question."""
    return Expansion(expansion.language, source.query, list(source.terms),
                     [], {"shuffled_control": {"terms": list(source.terms)}}, [])


__all__ = [
    "LANGUAGES",
    "N_TERMS_PER_CONCEPT",
    "MAX_QUERY_TERMS",
    "MIN_TERM_CHARS",
    "MIN_TERM_DF",
    "CorpusSample",
    "Expansion",
    "build_expansion",
    "blanked",
    "shuffled",
    "compound_stems",
    "norm",
    "tokens",
]
