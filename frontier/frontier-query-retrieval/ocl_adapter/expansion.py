"""Query variant construction (FR/DE/IT) without fabricated translations.

Two independent, provenance-preserving expansion mechanisms:

* ``lexicon_expansion`` - appends synonym terms drawn **only** from the
  accepted LexMachina legal lexicon (see :mod:`.lexicon`). Nothing is
  translated; unknown terms simply add nothing.
* ``language_filter``   - re-issues the original query with the OpenCaseLaw
  ``language=de|fr|it`` filter, which is a server-side filter, not a
  translation.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence

from . import lexicon

TOKEN_RE = re.compile(r"[^\W\d_]+", re.UNICODE)


def tokenize(text: str) -> List[str]:
    return [t.lower() for t in TOKEN_RE.findall(text or "") if len(t) > 1]


@dataclass(frozen=True)
class QueryVariant:
    variant_id: str
    text: str
    kind: str                # original | lexicon_expansion | language_filter
    language_filter: Optional[str] = None
    terms_added: tuple = ()
    terms_added_from: str = ""
    note: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["terms_added"] = list(self.terms_added)
        return d


def _vid(kind: str, lang: Optional[str], text: str) -> str:
    digest = hashlib.sha1(f"{kind}|{lang or ''}|{text}".encode("utf-8")).hexdigest()[:8]
    return f"{kind}:{lang or 'any'}:{digest}"


def build_variants(
    query: str,
    language_filters: Sequence[str] = ("de", "fr", "it"),
    *,
    max_terms: int = 12,
    include_language_filters: bool = True,
) -> List[QueryVariant]:
    """Deterministic, provenance-preserving variant list for one query."""
    query = (query or "").strip()
    if not query:
        raise ValueError("empty query")

    variants: List[QueryVariant] = [
        QueryVariant(
            variant_id=_vid("original", None, query),
            text=query,
            kind="original",
            note="user query, unmodified",
        )
    ]

    toks = tokenize(query)
    known = set(toks)
    added: List[str] = []
    for tok in toks:
        for term in lexicon.lookup(tok):
            if term in known or term in added:
                continue
            added.append(term)
        if len(added) >= max_terms:
            break
    added = added[:max_terms]
    if added:
        variants.append(
            QueryVariant(
                variant_id=_vid("lexicon_expansion", None, query + " " + " ".join(added)),
                text=(query + " " + " ".join(added)).strip(),
                kind="lexicon_expansion",
                terms_added=tuple(added),
                terms_added_from=lexicon.LEXICON_PROVENANCE,
                note="accepted LexMachina lexicon synonyms only; no machine translation",
            )
        )

    if include_language_filters:
        for lang in language_filters:
            variants.append(
                QueryVariant(
                    variant_id=_vid("language_filter", lang, query),
                    text=query,
                    kind="language_filter",
                    language_filter=lang,
                    note=f"server-side OpenCaseLaw language={lang} filter (not a translation)",
                )
            )
    return variants


def search_variants(variants: Sequence[QueryVariant]) -> List[QueryVariant]:
    """Variants that should hit ``/decisions`` (original + lexicon expansion)."""
    return [v for v in variants if v.kind in ("original", "lexicon_expansion")]


def language_variants(variants: Sequence[QueryVariant]) -> List[QueryVariant]:
    return [v for v in variants if v.kind == "language_filter"]


def all_terms(variants: Sequence[QueryVariant]) -> List[str]:
    out: List[str] = []
    for v in variants:
        for t in v.terms_added:
            if t not in out:
                out.append(t)
    return out
