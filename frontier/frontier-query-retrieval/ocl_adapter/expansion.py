"""Query variant construction (FR/DE/IT) with auditable legal expansion.

Expansion is deterministic and source-transparent.  It deliberately avoids
free-form machine translation on the retrieval hot path:

* fixed accepted legal lexicon synonyms;
* Swiss statute aliases (e.g. art. 102 CP -> Art. 102 StGB);
* a small set of doctrine / legal-concept aliases whose exact strings are
  versioned here and surfaced in provenance;
* server-side language filters for the original query.

The purpose of the concept layer is not to answer the legal question.  It is
only to bridge terminology that Swiss case law often expresses in another
official language or under a doctrine name different from the user's wording.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from typing import List, Optional, Sequence, Tuple

from . import lexicon

TOKEN_RE = re.compile(r"[^\W\d_]+", re.UNICODE)
ARTICLE_RE = re.compile(
    r"(?i)\bart(?:\.|icle)?\s*(\d+[a-z]?)"
    r"(?:\s*(?:al\.|alin[ée]a|abs\.|cpv\.)\s*\d+)?"
    r"\s*(CP|CO|CC|CPC|CPP|LTF|StGB|OR|ZGB|ZPO|StPO|BGG)\b"
)

# Swiss code abbreviations frequently differ by language.  Compact article-only
# variants are intentionally independent searches: appending a German code
# abbreviation to a long French sentence can make lexical FTS worse.
STATUTE_EQUIVALENTS = {
    "CP": ("StGB",),
    "STGB": ("CP",),
    "CO": ("OR",),
    "OR": ("CO",),
    "CC": ("ZGB",),
    "ZGB": ("CC",),
    "CPC": ("ZPO",),
    "ZPO": ("CPC",),
    "CPP": ("StPO",),
    "STPO": ("CPP",),
    "LTF": ("BGG",),
    "BGG": ("LTF",),
}

# Doctrine aliases are retrieval vocabulary, not legal propositions.  They are
# deliberately compact and auditable.  Matching is conservative: at least one
# trigger phrase must occur in the user's query.
CONCEPT_VARIANTS: Tuple[Tuple[Tuple[str, ...], Tuple[str, ...]], ...] = (
    (
        ("business judgment rule", "business judgement rule", "règle de l'appréciation commerciale"),
        (
            "Business Judgment Rule Verwaltungsrat",
            "Geschäftsentscheid Verwaltungsrat angemessene Informationsbasis Interessenkonflikt",
            "unternehmerischer Entscheid Verwaltungsrat Art. 754 OR",
        ),
    ),
    (
        ("licenciement immédiat", "résiliation immédiate", "fristlose kündigung"),
        (
            "fristlose Kündigung Arbeitnehmer Art. 337 OR",
            "wichtiger Grund Arbeitsvertrag Art. 337 OR",
        ),
    ),
    (
        ("vol de faible valeur", "vol de peu de valeur", "petit vol", "diebstahl"),
        (
            "Diebstahl Arbeitnehmer fristlose Kündigung",
            "geringfügiger Diebstahl fristlose Kündigung",
            "Bagatelldiebstahl fristlose Kündigung",
            "Diebstahl Arbeitgeber Vertrauensverhältnis",
            "Diebstahl Art. 337 OR",
        ),
    ),
    (
        ("responsabilité pénale de l'entreprise", "responsabilité de l'entreprise", "unternehmensstrafbarkeit"),
        (
            "Unternehmensstrafbarkeit Art. 102 StGB",
            "Unternehmen Organisationsmangel Art. 102 Abs. 1 StGB",
            "Unternehmen Organisationsmassnahmen Art. 102 Abs. 2 StGB",
        ),
    ),
    (
        ("retard dans le paiement du loyer", "défaut de paiement du loyer", "zahlungsrückstand"),
        (
            "Zahlungsrückstand Miete Kündigung Art. 257d OR",
            "Zahlungsfrist 30 Tage Art. 257d OR",
        ),
    ),
)


def tokenize(text: str) -> List[str]:
    return [t.lower() for t in TOKEN_RE.findall(text or "") if len(t) > 1]


@dataclass(frozen=True)
class QueryVariant:
    variant_id: str
    text: str
    kind: str  # original | lexicon_expansion | statute_alias | legal_concept | language_filter
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


def _legal_query_variants(query: str) -> List[Tuple[str, str, str]]:
    """Return deterministic compact legal aliases as (kind, text, note)."""
    out: List[Tuple[str, str, str]] = []
    seen = {query.casefold()}

    for m in ARTICLE_RE.finditer(query):
        number, code = m.group(1), m.group(2).upper()
        for alias in STATUTE_EQUIVALENTS.get(code, ()):
            text = f"Art. {number} {alias}"
            if text.casefold() not in seen:
                seen.add(text.casefold())
                out.append((
                    "statute_alias",
                    text,
                    f"Swiss statute abbreviation alias {code}->{alias}; article number preserved",
                ))

    folded = " ".join((query or "").casefold().split())
    for triggers, variants in CONCEPT_VARIANTS:
        if not any(trigger.casefold() in folded for trigger in triggers):
            continue
        for text in variants:
            if text.casefold() in seen:
                continue
            seen.add(text.casefold())
            out.append((
                "legal_concept",
                text,
                "versioned Swiss legal-concept retrieval alias; not an answer or machine translation",
            ))
    return out


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

    for kind, text, note in _legal_query_variants(query):
        variants.append(
            QueryVariant(
                variant_id=_vid(kind, None, text),
                text=text,
                kind=kind,
                terms_added=tuple(tokenize(text)),
                terms_added_from="ocl_adapter.expansion:versioned_legal_aliases",
                note=note,
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
    """Variants that should hit /decisions as independent relevance searches."""
    return [
        v for v in variants
        if v.kind in ("original", "lexicon_expansion", "statute_alias", "legal_concept")
    ]


def language_variants(variants: Sequence[QueryVariant]) -> List[QueryVariant]:
    return [v for v in variants if v.kind == "language_filter"]


def all_terms(variants: Sequence[QueryVariant]) -> List[str]:
    out: List[str] = []
    for v in variants:
        for t in v.terms_added:
            if t not in out:
                out.append(t)
    return out
