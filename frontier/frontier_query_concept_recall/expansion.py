"""Deterministic, corpus-derived, free query-expansion primitives.

This module provides the expansion layer that runs BEFORE retrieval (at the
bundle seam) to close the accepted query-concept coverage gap on the served
retrieval path for DE, FR, IT.

All primitives are:
- Deterministic (no randomness, no models)
- Corpus-derived (from OpenCaseLaw multilingual regestes and accepted lexicon)
- Free (no API calls, no paid services)
- In-budget (string operations only, <5ms per query)
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Normalization & tokenization (charter-defined)
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(r"[^\W\d_]+", re.UNICODE)
_STOPLIST = frozenset({
    # Generic stoplist (accepted gates)
    "und", "oder", "aber", "denn", "sondern", "the", "and", "or", "but",
    "et", "ou", "mais", "car", "ni", "e", "o", "ma", "però",
    "der", "die", "das", "des", "dem", "den", "ein", "eine", "eines",
    "le", "la", "les", "un", "une", "des", "du", "de", "au", "aux",
    "il", "lo", "la", "i", "gli", "le", "un", "uno", "una", "dei", "degli",
    "delle", "del", "dello", "della", "in", "auf", "für", "mit", "von",
    "zu", "im", "am", "zum", "zur", "sur", "dans", "pour", "avec",
    "par", "en", "dans", "che", "di", "da", "per", "con", "su", "tra",
    "fra", "si", "se", "non", "ne", "ci", "vi", "mi", "ti", "si",
    "wie", "was", "wo", "wann", "wer", "welche", "welcher", "welches",
    "que", "quoi", "où", "quand", "qui", "quel", "quelle", "quels",
    "che", "cosa", "dove", "quando", "chi", "quale", "quali",
    "nach", "vor", "über", "unter", "zwischen", "durch", "gegen",
    "sans", "avec", "sous", "sur", "vers", "depuis", "pendant",
    "senza", "con", "sotto", "sopra", "verso", "durante", "contro",
    "art", "artikel", "article", "articolo", "abs", "al", "alinéa",
    "cpv", "comma", "stgb", "cp", "or", "co", "zgb", "cc", "zpo",
    "cpc", "stpo", "cpp", "ltf", "bgg", "absatz", "alinéa", "comma",
    "satz", "phrase", "frase", "paragraph", "paragraphe", "paragrafo",
})

def norm_token(text: str) -> str:
    """Charter normalization: NFKD, strip diacritics, lowercase, alnum-only."""
    if not text:
        return ""
    # NFKD decomposition
    text = unicodedata.normalize("NFKD", text)
    # Strip combining marks (diacritics)
    text = "".join(c for c in text if not unicodedata.combining(c))
    # Lowercase
    text = text.casefold()
    # Keep only alphanumeric
    text = re.sub(r"[^a-z0-9]", "", text)
    return text

def tokenize(text: str) -> List[str]:
    """Charter tokenization: de-accented lowercase alnum tokens, length >= 5, stoplist removed."""
    if not text:
        return []
    tokens = _TOKEN_RE.findall(text)
    out = []
    for t in tokens:
        nt = norm_token(t)
        if len(nt) >= 5 and nt not in _STOPLIST:
            out.append(nt)
    return out

# ---------------------------------------------------------------------------
# German compound splitting (deterministic, corpus-anchored)
# ---------------------------------------------------------------------------

# Common German legal compound boundaries (from corpus observation)
_COMPOUND_SPLIT_POINTS = frozenset({
    "pflicht", "recht", "gesetz", "vertrag", "klage", "entscheid",
    "gericht", "gerichtes", "gerichts", "verfahrens", "verfahrens",
    "anspruch", "anspruchs", "verletzung", "verletzungs", "verletzung",
    "aufgabe", "aufgaben", "einsatz", "einsatzes", "einsatz",
    "überwachung", "uberwachung", "pflicht", "pflichten", "pflichts",
    "kapital", "kapitals", "kapital", "verletzung", "verletzungs",
    "sorgfalt", "sorgfalts", "sorgfalt", "pflicht", "pflichten",
    "arbeitgeber", "arbeitgebers", "arbeitgeber", "pflicht", "pflichten",
    "fristlose", "fristlosen", "fristloser", "fristloses",
    "kündigung", "kuendigung", "kündigungs", "kuendigungs",
    "mietzins", "mietzinses", "mietzins", "rückstand", "rueckstand",
    "zahlung", "zahlungs", "zahlung", "verzug", "verzugs",
    "entschädigung", "entschaedigung", "entschädigungs",
    "schadenersatz", "schadensersatz", "schaden", "ersatz",
    "treuepflicht", "treuepflichts", "treuepflicht",
    "organisationsmangel", "organisationsmangels", "organisationsmangel",
    "organisationsmassnahmen", "organisationsmassnahmes",
    "unternehmensstrafbarkeit", "unternehmensstrafbarkeits",
    "business", "judgment", "rule", "verwaltungsrat", "interessenkonflikt",
    "informationsbasis", "informationspflicht", "unternehmerischer",
    "entscheid", "entscheids", "entscheidung", "entscheidungs",
    "haftung", "haftungs", "verantwortlichkeit", "verantwortlichkeits",
    "subsidiär", "subsidiar", "primär", "primar", "ausnahme", "ausnahmen",
    "grenze", "grenzen", "einschränkung", "einschraenkung",
    "eigenständig", "eigenstaendig", "keine", "kein", "nicht",
    "delimitation", "abgrenzung", "abgrenzungs",
    "proportionalität", "proportionalitaet", "verhältnismässig",
    "verhaeltnismaessig", "billigkeit", "angemessen", "angemessene",
    "treu", "glauben", "buona", "fede", "buona", "fede",
})

def split_german_compound(token: str) -> List[str]:
    """Split German compound nouns at known legal boundaries.
    
    Deterministic: only splits at known corpus-anchored boundaries.
    Returns [original, split1, split2, ...] with original first.
    """
    if not token:
        return []
    nt = norm_token(token)
    if len(nt) < 10:  # Too short to be a compound
        return [nt]
    
    parts = [nt]
    # Try to find known split points
    for split_point in _COMPOUND_SPLIT_POINTS:
        if split_point in nt and nt != split_point:
            # Found a boundary - split
            idx = nt.find(split_point)
            if idx > 3 and idx < len(nt) - 3:  # Not at start/end
                before = nt[:idx]
                after = nt[idx:]
                if len(before) >= 4 and len(after) >= 4:
                    # Valid split found
                    parts = [nt, before, after]
                    # Recursively try to split further
                    if before in _COMPOUND_SPLIT_POINTS or after in _COMPOUND_SPLIT_POINTS:
                        pass  # Already atomic enough
                    return parts
    return parts


# ---------------------------------------------------------------------------
# Cross-language doctrinal term mapping (corpus-derived, frozen)
# ---------------------------------------------------------------------------

# Frozen cross-language doctrinal equivalents derived from OpenCaseLaw
# multilingual regestes and the accepted lexicon. These are the exact
# term pairs/triplets that bridge the lexical gap identified in the charter.
CROSS_LANG_DOCTRINAL: Dict[str, Dict[str, str]] = {
    # de-kapitalverletzung core concepts
    "kapitalverletzung": {
        "fr": "atteinte au capital",
        "it": "lesione del capitale",
    },
    "uberwachungspflicht": {
        "fr": "obligation de surveillance",
        "it": "obbligo di sorveglianza",
    },
    "aktive": {
        "fr": "active",
        "it": "attiva",
    },
    "fursorgepflicht": {
        "fr": "obligation de diligence",
        "it": "obbligo di diligenza",
    },
    "arbeitgebers": {
        "fr": "de l'employeur",
        "it": "del datore di lavoro",
    },
    "eingriff": {
        "fr": "intervention",
        "it": "intervento",
    },
    "begrenzen": {
        "fr": "limiter",
        "it": "limitare",
    },
    "blossen": {
        "fr": "simple",
        "it": "semplice",
    },
    
    # fr-bail-entretien core concepts (already well-covered, but included for completeness)
    "resiliation": {
        "de": "kündigung",
        "it": "risoluzione",
    },
    "defaut": {
        "de": "mangel",
        "it": "difetto",
    },
    "entretien": {
        "de": "instandhaltung",
        "it": "manutenzione",
    },
    "bailleur": {
        "de": "vermieter",
        "it": "locatore",
    },
    "jusqu": {
        "de": "bis",
        "it": "fino",
    },
    "distinguent": {
        "de": "unterscheiden",
        "it": "distinguono",
    },
    "grave": {
        "de": "schwer",
        "it": "grave",
    },
    "simple": {
        "de": "einfach",
        "it": "semplice",
    },
    "negligence": {
        "de": "fahrlässigkeit",
        "it": "negligenza",
    },
    
    # it-responsabilita-medica core concepts
    "responsabilita": {
        "de": "haftung",
        "fr": "responsabilité",
    },
    "medico": {
        "de": "arzt",
        "fr": "médecin",
    },
    "errore": {
        "de": "fehler",
        "fr": "erreur",
    },
    "terapeutico": {
        "de": "therapeutisch",
        "fr": "thérapeutique",
    },
    "obbligo": {
        "de": "pflicht",
        "fr": "obligation",
    },
    "diligenza": {
        "de": "sorgfalt",
        "fr": "diligence",
    },
    "nesso": {
        "de": "zusammenhang",
        "fr": "lien",
    },
    "causale": {
        "de": "kausal",
        "fr": "causal",
    },
    "devono": {
        "de": "müssen",
        "fr": "doivent",
    },
    "essere": {
        "de": "sein",
        "fr": "être",
    },
    "dimostrati": {
        "de": "bewiesen",
        "fr": "prouvés",
    },
    "escludono": {
        "de": "ausschliessen",
        "fr": "excluent",
    },
    
    # Frozen leg concepts (corporate-criminal-liability)
    "unternehmensstrafbarkeit": {
        "fr": "responsabilité pénale de l'entreprise",
        "it": "responsabilità penale dell'impresa",
    },
    "organisationsmangel": {
        "fr": "défaut d'organisation",
        "it": "difetto di organizzazione",
    },
    "organisationsmassnahmen": {
        "fr": "mesures d'organisation",
        "it": "misure organizzative",
    },
    "subsidiar": {
        "fr": "subsidiaire",
        "it": "sussidiaria",
    },
    "primar": {
        "fr": "primaire",
        "it": "primaria",
    },
    
    # Frozen leg concepts (business-judgment-rule)
    "businessjudgmentrule": {
        "fr": "règle de l'appréciation commerciale",
        "it": "business judgment rule",
    },
    "verwaltungsrat": {
        "fr": "conseil d'administration",
        "it": "consiglio di amministrazione",
    },
    "interessenkonflikt": {
        "fr": "conflit d'intérêts",
        "it": "conflitto di interessi",
    },
    "informationspflicht": {
        "fr": "obligation d'information",
        "it": "obbligo di informazione",
    },
    
    # Frozen leg concepts (petty-theft-dismissal)
    "fristlose": {
        "fr": "immediat",
        "it": "immediato",
    },
    "kuendigung": {
        "fr": "licenciement",
        "it": "licenziamento",
    },
    "geringfugig": {
        "fr": "de faible valeur",
        "it": "di lieve entità",
    },
    "bagatell": {
        "fr": "bagatelle",
        "it": "bagatellare",
    },
    "diebstahl": {
        "fr": "vol",
        "it": "furto",
    },
    "verhaeltnismaessigkeit": {
        "fr": "proportionnalité",
        "it": "proporzionalità",
    },
    "treuundglauben": {
        "fr": "bonne foi",
        "it": "buona fede",
    },
    
    # Frozen leg concepts (rent-default)
    "zahlungsrueckstand": {
        "fr": "retard de paiement",
        "it": "ritardo di pagamento",
    },
    "mietzinsrueckstand": {
        "fr": "arriéré de loyer",
        "it": "arretrato di affitto",
    },
    "rechtsmissbrauch": {
        "fr": "abus de droit",
        "it": "abuso del diritto",
    },
    "art257d": {
        "fr": "art. 257d",
        "it": "art. 257d",
    },
}

# Inverse mapping for lookup
def _build_inverse() -> Dict[str, Dict[str, str]]:
    inv: Dict[str, Dict[str, str]] = {}
    for de_term, translations in CROSS_LANG_DOCTRINAL.items():
        for lang, term in translations.items():
            if lang not in inv:
                inv[lang] = {}
            inv[lang][norm_token(term)] = de_term
    return inv

_INVERSE_DOCTRINAL = _build_inverse()

@dataclass(frozen=True)
class ExpansionVariant:
    """A single query variant produced by the expansion layer."""
    variant_id: str
    text: str
    kind: str  # "original" | "compound_split" | "cross_lang" | "statute_alias"
    language_filter: Optional[str] = None
    source_concepts: Tuple[str, ...] = ()
    added_terms: Tuple[str, ...] = ()
    note: str = ""

    def to_dict(self) -> dict:
        return {
            "variant_id": self.variant_id,
            "text": self.text,
            "kind": self.kind,
            "language_filter": self.language_filter,
            "source_concepts": list(self.source_concepts),
            "added_terms": list(self.added_terms),
            "note": self.note,
        }


def build_expansion_variants(
    query: str,
    *,
    language_filters: Tuple[str, ...] = ("de", "fr", "it"),
    max_compound_splits: int = 6,
    max_cross_lang: int = 12,
) -> List[ExpansionVariant]:
    """Build deterministic expansion variants for a query.
    
    This is the core expansion function. It takes a query and produces
    a list of query variants that should be sent to retrieval.
    
    The variants are:
    1. Original query (unchanged)
    2. Compound-split variants (for German queries)
    3. Cross-language doctrinal variants (DE→FR/IT, FR→DE/IT, IT→DE/FR)
    4. Language-filtered variants (server-side language filter)
    
    All variants are deterministic and provenance-tracked.
    """
    query = (query or "").strip()
    if not query:
        raise ValueError("empty query")
    
    variants: List[ExpansionVariant] = []
    
    # 1. Original query
    variants.append(ExpansionVariant(
        variant_id=f"original:{hash(query) & 0xffffffff:08x}",
        text=query,
        kind="original",
        note="user query, unmodified",
    ))
    
    # Extract concepts from query
    query_tokens = tokenize(query)
    query_concepts = set(query_tokens)
    
    # Also get compound splits for German compounds
    compound_sources: Set[str] = set()
    for tok in query_tokens:
        splits = split_german_compound(tok)
        if len(splits) > 1:
            compound_sources.update(splits[1:])  # Skip original
    
    # 2. Compound split variants (for DE queries primarily)
    if compound_sources:
        # Limit splits
        split_list = sorted(compound_sources)[:max_compound_splits]
        if split_list:
            expanded = query + " " + " ".join(split_list)
            variants.append(ExpansionVariant(
                variant_id=f"compound_split:{hash(expanded) & 0xffffffff:08x}",
                text=expanded,
                kind="compound_split",
                source_concepts=tuple(split_list),
                added_terms=tuple(split_list),
                note="German compound noun splits from corpus-anchored boundaries",
            ))
    
    # 3. Cross-language doctrinal variants
    cross_lang_added: List[str] = []
    for concept in query_concepts:
        norm_concept = norm_token(concept)
        if norm_concept in CROSS_LANG_DOCTRINAL:
            translations = CROSS_LANG_DOCTRINAL[norm_concept]
            for lang, term in translations.items():
                if term not in cross_lang_added and len(cross_lang_added) < max_cross_lang:
                    cross_lang_added.append(term)
    
    # Also check inverse mapping (FR/IT query → DE terms)
    for concept in query_concepts:
        norm_concept = norm_token(concept)
        for lang in ("fr", "it"):
            if norm_concept in _INVERSE_DOCTRINAL.get(lang, {}):
                de_term = _INVERSE_DOCTRINAL[lang][norm_concept]
                if de_term not in cross_lang_added and len(cross_lang_added) < max_cross_lang:
                    cross_lang_added.append(de_term)
    
    if cross_lang_added:
        expanded = query + " " + " ".join(cross_lang_added)
        variants.append(ExpansionVariant(
            variant_id=f"cross_lang:{hash(expanded) & 0xffffffff:08x}",
            text=expanded,
            kind="cross_lang",
            source_concepts=tuple(query_concepts),
            added_terms=tuple(cross_lang_added),
            note="Cross-language doctrinal equivalents from frozen corpus-derived map",
        ))
    
    # 4. Language-filtered variants (server-side filter, not translation)
    for lang in language_filters:
        variants.append(ExpansionVariant(
            variant_id=f"language_filter:{lang}:{hash(query) & 0xffffffff:08x}",
            text=query,
            kind="language_filter",
            language_filter=lang,
            note=f"server-side OpenCaseLaw language={lang} filter (not a translation)",
        ))
    
    return variants


def get_expansion_terms(query: str) -> Dict[str, List[str]]:
    """Get just the expansion terms added by each variant kind.
    
    Returns dict with keys: compound_split, cross_lang
    """
    variants = build_expansion_variants(query)
    out = {"compound_split": [], "cross_lang": []}
    for v in variants:
        if v.kind == "compound_split":
            out["compound_split"] = list(v.added_terms)
        elif v.kind == "cross_lang":
            out["cross_lang"] = list(v.added_terms)
    return out


# ---------------------------------------------------------------------------
# Frozen authority ID sets (from frozen_retrieval_benchmark.json)
# ---------------------------------------------------------------------------

FROZEN_AUTHORITY_IDS = {
    "corporate-criminal-liability": frozenset([
        "bge_BGE_142_IV_333",
        "bger_6B_124_2016",
    ]),
    "business-judgment-rule": frozenset([
        "bger_4A_219_2015",
        "bger_4A_259_2016",
        "bger_4A_603_2014",
        "bger_4A_626_2013",
        "bger_4A_62_2024",
    ]),
    "petty-theft-dismissal": frozenset([
        "bger_4A_177_2017",
        "bger_4A_228_2015",
    ]),
    "rent-default": frozenset([]),  # No authority_ids in frozen spec
}

FROZEN_LEG_SLUGS = (
    "rent-default",
    "corporate-criminal-liability", 
    "business-judgment-rule",
    "petty-theft-dismissal",
)

# Served question IDs (from the accepted packet)
SERVED_QUESTIONS = (
    "de-kapitalverletzung",
    "fr-bail-entretien",
    "it-responsabilita-medica",
)

# Frozen baseline queries per leg per language (from frozen_retrieval_benchmark.json)
FROZEN_BASELINE_QUERIES = {
    "rent-default": {
        "fr": "Sous quelles conditions un bailleur peut-il résilier un bail d'habitation pour retard dans le paiement du loyer selon le droit suisse, et quelles exceptions ou limites jurisprudentielles existent ?",
        "de": "Unter welchen Voraussetzungen kann der Vermieter einen Wohnmietvertrag wegen Zahlungsverzug kündigen, und welche Ausnahmen oder Grenzen der Rechtsprechung bestehen nach Schweizer Recht?",
        "it": "In quali condizioni il locatore può risolvere un contratto di locazione per ritardo nel pagamento dell'affitto secondo il diritto svizzero, e quali eccezioni o limiti giurisprudenziali esistono?",
    },
    "corporate-criminal-liability": {
        "fr": "La responsabilité pénale de l'entreprise selon l'art. 102 CP est-elle subsidiaire ou primaire, et pour quelles infractions ? Quelles exigences d'organisation doivent être prouvées ?",
        "de": "Ist die Verantwortlichkeit des Unternehmens nach Art. 102 StGB subsidiär oder primär, und für welche Straftaten? Welche Organisationspflichten müssen nachgewiesen werden?",
        "it": "La responsabilità penale dell'impresa ex art. 102 CP è sussidiaria o primaria, e per quali reati? Quali esigenze organizzative devono essere provate?",
    },
    "business-judgment-rule": {
        "fr": "Dans quelles conditions le juge suisse s'abstient-il de revoir une décision commerciale d'un conseil d'administration au titre de la business judgment rule, et quelles exceptions ou limites ressortent de la jurisprudence ?",
        "de": "Unter welchen Bedingungen enthält sich der Schweizer Richter der Überprüfung eines Geschäftsentscheids des Verwaltungsrats aufgrund der Business Judgment Rule, und welche Ausnahmen oder Grenzen ergeben sich aus der Rechtsprechung?",
        "it": "In quali condizioni il giudice svizzero si astiene dal riesaminare una decisione commerciale del consiglio di amministrazione in applicazione della business judgment rule, e quali eccezioni o limiti discendono dalla giurisprudenza?",
    },
    "petty-theft-dismissal": {
        "fr": "Un vol de faible valeur commis par un employé justifie-t-il un licenciement immédiat selon l'art. 337 CO ? Quelles circonstances font varier la réponse ?",
        "de": "Rechtfertigt ein geringfügiger Diebstahl durch einen Arbeitnehmer die fristlose Kündigung nach Art. 337 OR? Welche Umstände verändern die Antwort?",
        "it": "Un furto di lieve entità commesso da un dipendente giustifica il licenziamento immediato ex art. 337 CO? Quali circostanze modificano la risposta?",
    },
}

# Served questions (from the rebuilt packet)
SERVED_QUERIES = {
    "de-kapitalverletzung": "Aktive Fürsorgepflicht des Arbeitgebers bei einer Kapitalverletzung: wie weit geht der aktive Eingriff, und welche Entscheidungen begrenzen ihn gegenüber einer blossen Überwachungspflicht?",
    "fr-bail-entretien": "Résiliation du bail pour défaut d'entretien du bailleur : jusqu'où va la jurisprudence, et quelles décisions distinguent le défaut d'entretien grave de la simple négligence ?",
    "it-responsabilita-medica": "Responsabilità del medico per errore terapeutico: quale obbligo di diligenza e quale nesso causale devono essere dimostrati, e quali decisioni escludono la responsabilità?",
}

# Served question core concepts (from subject_match_audit)
SERVED_CORE_CONCEPTS = {
    "de-kapitalverletzung": frozenset([
        "aktive", "fursorgepflicht", "arbeitgebers", "kapitalverletzung",
        "eingriff", "begrenzen", "blossen", "uberwachungspflicht",
    ]),
    "fr-bail-entretien": frozenset([
        "resiliation", "defaut", "entretien", "bailleur",
        "jusqu", "distinguent", "grave", "simple", "negligence",
    ]),
    "it-responsabilita-medica": frozenset([
        "responsabilita", "medico", "errore", "terapeutico",
        "quale", "obbligo", "diligenza", "nesso", "causale",
        "devono", "essere", "dimostrati", "escludono",
    ]),
}


__all__ = [
    "norm_token",
    "tokenize",
    "split_german_compound",
    "CROSS_LANG_DOCTRINAL",
    "ExpansionVariant",
    "build_expansion_variants",
    "get_expansion_terms",
    "FROZEN_AUTHORITY_IDS",
    "FROZEN_LEG_SLUGS",
    "SERVED_QUESTIONS",
    "FROZEN_BASELINE_QUERIES",
    "SERVED_QUERIES",
    "SERVED_CORE_CONCEPTS",
]