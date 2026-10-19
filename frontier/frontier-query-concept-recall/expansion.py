"""Deterministic multilingual query-expansion layer for concept recall.

This module implements the expansion layer behind the existing bundle seam.
It does NOT modify the retrieval adapter, classifier, layout, or national corpus.
It adds ONE deterministic expansion layer measured behind the existing bundle seam.

Key design principles:
- Corpus-derived: uses existing CONCEPT_VARIANTS from ocl_adapter.expansion
- Deterministic: no ML, no generation, fixed lookup tables
- Additive: query variants and provenance entries are additive and backwards-compatible
- Drop-in: integrates with existing product.query.pipeline via query_variants field
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Set, Tuple, Dict, Any

# Frozen generic stoplist (from accepted evaluation)
GENERIC_STOPLIST = frozenset({
    "the", "and", "for", "are", "but", "not", "you", "all", "any", "can", "her", "was", "one", "our", "out", "day", "get", "has", "him", "his", "how", "its", "may", "new", "now", "old", "see", "two", "way", "who", "boy", "did", "man", "put", "say", "she", "too", "use",
    "der", "die", "das", "und", "oder", "aber", "nicht", "ein", "eine", "einer", "eines", "einem", "den", "dem", "des", "von", "zu", "mit", "auf", "für", "ist", "sind", "war", "waren", "hat", "haben", "hatte", "hatten", "wird", "werden", "kann", "können", "muss", "müssen", "soll", "sollen", "will", "wollen", "ist", "bin", "bist", "sind", "seid",
    "le", "la", "les", "un", "une", "des", "du", "de", "et", "ou", "mais", "non", "est", "sont", "etait", "etaient", "a", "ont", "avait", "avaient", "sera", "seront", "peut", "peuvent", "doit", "doivent", "veut", "veulent", "je", "tu", "il", "elle", "nous", "vous", "ils", "elles", "ce", "cette", "ces", "mon", "ton", "son", "ma", "ta", "sa", "mes", "tes", "ses",
    "il", "lo", "la", "i", "gli", "le", "un", "uno", "una", "dei", "degli", "delle", "e", "o", "ma", "non", "e", "sono", "era", "erano", "ha", "hanno", "aveva", "avevano", "sara", "saranno", "puo", "possono", "deve", "devono", "vuole", "vogliono", "io", "tu", "lui", "lei", "noi", "voi", "loro", "questo", "questa", "questi", "queste", "mio", "tuo", "suo", "mia", "tua", "sua", "miei", "tuoi", "suoi",
    "selon", "selon", "dans", "pour", "avec", "sans", "sur", "sous", "par", "qui", "que", "quoi", "dont", "ou", "et", "mais", "donc", "car", "ni", "si", "aussi", "ainsi", "alors", "done", "encore", "deja", "toujours", "souvent", "parfois", "jamais", "ici", "la", "la", "ou", "ou", "bien", "mal", "mieux", "pire",
    "secondo", "per", "con", "senza", "su", "sotto", "da", "chi", "che", "cosa", "cui", "o", "e", "ma", "non", "quindi", "allora", "anche", "ancora", "già", "sempre", "spesso", "qualche volta", "mai", "qui", "là", "bene", "male", "meglio", "peggio",
    "where", "when", "what", "which", "who", "whom", "whose", "why", "how", "whether", "if", "then", "than", "that", "this", "these", "those", "there", "here", "now", "then", "before", "after", "above", "below", "between", "among", "through", "during", "since", "until", "while", "because", "although", "though", "even", "just", "only", "also", "both", "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not", "very", "too", "so", "can", "will", "would", "should", "could", "may", "might", "must", "shall",
})

# Token regex: de-accented lowercase alnum tokens (NFKD + strip diacritics + lowercase)
TOKEN_RE = re.compile(r"[^\W\d_]+", re.UNICODE)

# Article regex for statute aliases (from ocl_adapter.expansion)
ARTICLE_RE = re.compile(
    r"(?i)\bart(?:\.|icle)?\s*(\d+[a-z]?)"
    r"(?:\s*(?:al\.|alin[ée]a|abs\.|cpv\.)\s*\d+)?"
    r"\s*(CP|CO|CC|CPC|CPP|LTF|StGB|OR|ZGB|ZPO|StPO|BGG)\b"
)

# Statute equivalents (from ocl_adapter.expansion)
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

# Doctrine aliases from ocl_adapter.expansion CONCEPT_VARIANTS
# Each entry: (triggers_tuple, variants_tuple)
CONCEPT_VARIANTS = (
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
            "Art. 257d Abs. 2 OR Kündigungsfrist 30 Tage Ende eines Monats",
            "Art. 257d al. 2 CO préavis 30 jours fin d'un mois",
        ),
    ),
)


@dataclass(frozen=True)
class QueryVariant:
    """A deterministic query variant with full provenance."""
    variant_id: str
    text: str
    kind: str  # original | lexicon_expansion | statute_alias | legal_concept | language_filter | cross_language_concept
    language_filter: Optional[str] = None
    terms_added: Tuple[str, ...] = ()
    terms_added_from: str = ""
    note: str = ""

    def to_dict(self) -> dict:
        return {
            "variant_id": self.variant_id,
            "text": self.text,
            "kind": self.kind,
            "language_filter": self.language_filter,
            "terms_added": list(self.terms_added),
            "terms_added_from": self.terms_added_from,
            "note": self.note,
        }


def _vid(kind: str, lang: Optional[str], text: str) -> str:
    """Deterministic variant ID."""
    digest = hashlib.sha1(f"{kind}|{lang or ''}|{text}".encode("utf-8")).hexdigest()[:8]
    return f"{kind}:{lang or 'any'}:{digest}"


def _normalize_token(token: str) -> str:
    """Normalize token: NFKD, strip diacritics, lowercase, alnum only."""
    import unicodedata
    normalized = unicodedata.normalize('NFKD', token)
    stripped = ''.join(c for c in normalized if not unicodedata.combining(c))
    return stripped.lower()


def tokenize(text: str) -> List[str]:
    """Tokenize text into de-accented lowercase alnum tokens, len >= 2."""
    return [t for t in TOKEN_RE.findall(text or "") if len(t) > 1]


def extract_core_concepts(question: str) -> List[str]:
    """Extract core concepts from a question per the accepted definition.

    Core concepts = de-accented lowercase alnum tokens of the question text,
    length >= 5, the accepted generic stoplist removed.
    """
    tokens = tokenize(question)
    concepts = []
    seen = set()
    for tok in tokens:
        norm = _normalize_token(tok)
        if len(norm) >= 5 and norm not in GENERIC_STOPLIST and norm not in seen:
            seen.add(norm)
            concepts.append(norm)
    return concepts


def _legal_query_variants(query: str) -> List[Tuple[str, str, str]]:
    """Return deterministic compact legal aliases as (kind, text, note).

    Reuses the logic from ocl_adapter.expansion._legal_query_variants.
    """
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


def build_cross_language_concept_variants(
    query: str,
    core_concepts: List[str],
    query_language: str,
    target_languages: Sequence[str] = ("de", "fr", "it"),
) -> List[QueryVariant]:
    """Build cross-language concept variants for languages the query was NOT asked in.

    This is the key mechanism to raise cross-language authority recall.
    For each core concept, we look up known multilingual equivalents from the
    corpus-derived CONCEPT_VARIANTS and statute aliases.
    """
    variants: List[QueryVariant] = []
    seen_texts = {query.casefold()}

    # Build a mapping from concept triggers to their multilingual variants
    concept_to_variants: Dict[str, List[str]] = {}
    for triggers, variant_list in CONCEPT_VARIANTS:
        for trigger in triggers:
            trigger_norm = _normalize_token(trigger)
            if trigger_norm not in concept_to_variants:
                concept_to_variants[trigger_norm] = []
            concept_to_variants[trigger_norm].extend(variant_list)

    # For each core concept, find cross-language expansions
    added_terms: List[str] = []
    for concept in core_concepts:
        # Direct lookup in concept_to_variants
        if concept in concept_to_variants:
            for variant_text in concept_to_variants[concept]:
                if variant_text.casefold() not in seen_texts:
                    seen_texts.add(variant_text.casefold())
                    added_terms.append(variant_text)

        # Also check statute aliases for concepts that look like article references
        for m in ARTICLE_RE.finditer(query):
            number, code = m.group(1), m.group(2).upper()
            for alias in STATUTE_EQUIVALENTS.get(code, ()):
                text = f"Art. {number} {alias}"
                if text.casefold() not in seen_texts:
                    seen_texts.add(text.casefold())
                    added_terms.append(text)

    # Add language-filtered variants for target languages (not the query's own language)
    for lang in target_languages:
        if lang == query_language:
            continue
        variants.append(QueryVariant(
            variant_id=_vid("language_filter", lang, query),
            text=query,
            kind="language_filter",
            language_filter=lang,
            note=f"server-side OpenCaseLaw language={lang} filter (not a translation)",
        ))

    # Add cross-language concept expansion if we have added terms
    if added_terms:
        expanded_text = (query + " " + " ".join(added_terms)).strip()
        variants.append(QueryVariant(
            variant_id=_vid("cross_language_concept", None, expanded_text),
            text=expanded_text,
            kind="cross_language_concept",
            terms_added=tuple(added_terms),
            terms_added_from="corpus_derived_concept_variants + statute_aliases",
            note="deterministic cross-language concept expansion from frozen CONCEPT_VARIANTS and statute aliases",
        ))

    return variants


@dataclass(frozen=True)
class ExpansionConfig:
    """Configuration for the expansion layer."""
    max_lexicon_terms: int = 12
    include_language_filters: bool = True
    target_languages: Tuple[str, ...] = ("de", "fr", "it")
    include_cross_language_concepts: bool = True
    include_statute_aliases: bool = True
    include_legal_concepts: bool = True


def build_variants(
    query: str,
    query_language: str,
    config: Optional[ExpansionConfig] = None,
) -> List[QueryVariant]:
    """Build deterministic, provenance-preserving variant list for one query.

    This is the main entry point that replaces/extends ocl_adapter.expansion.build_variants.
    It adds cross-language concept expansion on top of the existing expansion logic.
    """
    if config is None:
        config = ExpansionConfig()

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

    # Lexicon expansion (from accepted product lexicon)
    toks = tokenize(query)
    known = set(toks)
    added: List[str] = []
    for tok in toks:
        # Import here to avoid circular dependency
        from product.frontier.frontier_query_retrieval.ocl_adapter import lexicon
        for term in lexicon.lookup(tok):
            if term in known or term in added:
                continue
            added.append(term)
        if len(added) >= config.max_lexicon_terms:
            break
    added = added[:config.max_lexicon_terms]
    if added:
        variants.append(
            QueryVariant(
                variant_id=_vid("lexicon_expansion", None, query + " " + " ".join(added)),
                text=(query + " " + " ".join(added)).strip(),
                kind="lexicon_expansion",
                terms_added=tuple(added),
                terms_added_from="accepted_lexicon",
                note="accepted LexMachina lexicon synonyms only; no machine translation",
            )
        )

    # Statute aliases
    if config.include_statute_aliases:
        for kind, text, note in _legal_query_variants(query):
            if kind == "statute_alias":
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

    # Legal concept variants (doctrine aliases)
    if config.include_legal_concepts:
        for kind, text, note in _legal_query_variants(query):
            if kind == "legal_concept":
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

    # Cross-language concept expansion (THE KEY ADDITION)
    if config.include_cross_language_concepts:
        core_concepts = extract_core_concepts(query)
        cross_lang = build_cross_language_concept_variants(
            query, core_concepts, query_language, config.target_languages
        )
        variants.extend(cross_lang)

    # Language filters (server-side OpenCaseLaw language filter)
    elif config.include_language_filters:
        for lang in config.target_languages:
            if lang == query_language:
                continue
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
        if v.kind in ("original", "lexicon_expansion", "statute_alias", "legal_concept", "cross_language_concept")
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


# --- Measurement functions for the acceptance tests ---

def measure_concept_coverage(
    decisions: List[dict],
    core_concepts: List[str],
) -> Dict[str, Any]:
    """Measure per-concept row coverage per the accepted definition.

    A concept is covered iff >= 1 bundle row's title/regeste/snippet/full_text/citation/decision_id
    contains it as a substring (permissive >= 1-of-set semantics).
    """
    concept_row_counts: Dict[str, int] = {c: 0 for c in core_concepts}

    for decision in decisions:
        # Searchable text fields
        searchable = " ".join(filter(None, [
            str(decision.get("title") or ""),
            str(decision.get("regeste") or ""),
            str(decision.get("snippet") or ""),
            str(decision.get("full_text") or ""),
            str(decision.get("citation") or ""),
            str(decision.get("decision_id") or ""),
        ])).lower()

        for concept in core_concepts:
            if concept.lower() in searchable:
                concept_row_counts[concept] += 1

    under_covered = [c for c, count in concept_row_counts.items() if count == 0]
    covered = [c for c, count in concept_row_counts.items() if count > 0]

    return {
        "concept_row_counts": concept_row_counts,
        "concepts": core_concepts,
        "concepts_with_zero_rows": under_covered,
        "concepts_covered": covered,
        "n_rows": len(decisions),
    }


def _alnum_core(s: str) -> str:
    """Compute alnum-core for authority ID matching (from frozen benchmark)."""
    import re
    core = re.sub(r"[^a-z0-9]", "", s.lower())
    # Strip repeated leading court tokens
    for prefix in ("bgestger", "bstger", "bger", "bge", "bg"):
        if core.startswith(prefix):
            core = core[len(prefix):]
            break
    return core


def measure_authority_recall(
    decisions: List[dict],
    frozen_authority_ids: List[str],
) -> Dict[str, Any]:
    """Measure recall of frozen authority IDs against retrieved decisions.

    Uses the same alnum-core matching as the frozen retrieval benchmark.
    """
    retrieved_ids = set()
    for d in decisions:
        for field in ("decision_id", "canonical_decision_id", "docket_number",
                      "citation_string_de", "citation_string_fr", "citation_string_it"):
            val = d.get(field)
            if val:
                retrieved_ids.add(_alnum_core(str(val)))

    frozen_cores = {_alnum_core(fid) for fid in frozen_authority_ids}
    matched = frozen_cores & retrieved_ids
    missing = frozen_cores - retrieved_ids

    # Per-language breakdown
    by_language: Dict[str, Dict[str, Any]] = {}
    for lang in ("de", "fr", "it"):
        lang_retrieved = set()
        for d in decisions:
            if d.get("language") == lang:
                for field in ("decision_id", "canonical_decision_id", "docket_number",
                              "citation_string_de", "citation_string_fr", "citation_string_it"):
                    val = d.get(field)
                    if val:
                        lang_retrieved.add(_alnum_core(str(val)))
        lang_matched = frozen_cores & lang_retrieved
        by_language[lang] = {
            "matched": len(lang_matched),
            "total": len(frozen_cores),
            "missing": list(frozen_cores - lang_retrieved),
        }

    return {
        "total_frozen": len(frozen_cores),
        "matched": len(matched),
        "missing": list(missing),
        "recall": len(matched) / len(frozen_cores) if frozen_cores else 1.0,
        "by_language": by_language,
    }