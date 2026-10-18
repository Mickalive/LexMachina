"""
Deterministic, corpus-derived multilingual query-expansion layer.

This module implements a drop-in expansion layer that sits behind the existing
bundle seam. It adds query variants derived from the retrieved corpus itself
(OpenCaseLaw decisions carry multilingual regestes) and from the existing
norm/citation channels, without rebuilding the retrieval adapter, classifier,
layout, or national corpus.

The expansion is:
- Deterministic: same input always produces same output
- Corpus-derived: terms come from the retrieved decisions' multilingual fields
- Free: no paid APIs, no model generation
- In-budget: negligible compute cost

Integration contract:
- Adds extra query_variants to the bundle (additive, backwards-compatible)
- Adds provenance entries describing the expansion
- Does not modify decisions, clusters, relations, or geometry
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any
from collections import OrderedDict

# ──────────────────────────────────────────────────────────────────────
# Normalization (must match product.query.concept_coverage.norm exactly)
# ──────────────────────────────────────────────────────────────────────

TOKEN_RE = re.compile(r"[^\W\d_]+", re.UNICODE)

def norm(value: Any) -> str:
    """NFKD, strip combining marks, casefold, collapse whitespace."""
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.casefold().split())


def tokenize(text: str) -> list[str]:
    return [t.casefold() for t in TOKEN_RE.findall(text or "")]


# ──────────────────────────────────────────────────────────────────────
# German compound splitter (deterministic, heuristic)
# ──────────────────────────────────────────────────────────────────────

# Common German legal compound components observed in Swiss case law
GERMAN_COMPOUND_SUFFIXES = frozenset([
    "pflicht", "verletzung", "schutz", "organ", "haftung", "klage", "rechts",
    "gericht", "entscheid", "urteil", "beschwerde", "rekurs", "verfahren",
    "massnahme", "vorschrift", "bestimmung", "norm", "artikel", "absatz",
    "satz", "ziffer", "buchstabe", "grund", "fall", "sache", "partei",
    "antrag", "beweis", "zeugnis", "gutachten", "sachverhalt", "erwaegung",
    "dispositiv", "kosten", "entschadigung", "genugtuung", "schaden",
    "ersatz", "verantwortung", "sorgfalt", "treue", "gegenstand", "inhalt",
    "umfang", "grenze", "ausnahme", "voraussetzung", "folge", "wirkung",
    "frist", "termin", "datum", "zeit", "ort", "person", "name", "titel",
    "funktion", "aufgabe", "recht", "pflicht", "macht", "befugnis", "kompetenz"
])

GERMAN_COMPOUND_PREFIXES = frozenset([
    "haupt", "neben", "vor", "nach", "zwischen", "uber", "unter", "gegen",
    "ohne", "mit", "selbst", "eigen", "fremd", "gesamt", "teil", "einzel",
    "gemein", "allein", "erst", "letzt", "hoechst", "mind", "mehr", "wenig",
    "neu", "alt", "groß", "klein", "lang", "kurz", "aktiv", "passiv",
    "direkt", "indirekt", "unmittelbar", "mittelbar", "rechtlich", "tatlich"
])

def split_german_compound(token: str) -> list[str]:
    """
    Deterministic heuristic splitter for German legal compounds.
    Returns the original token plus plausible splits.
    """
    token = token.casefold()
    if len(token) < 10:
        return [token]
    
    parts = [token]
    # Try to find known suffixes
    for suffix in GERMAN_COMPOUND_SUFFIXES:
        if token.endswith(suffix) and len(token) > len(suffix) + 3:
            prefix = token[:-len(suffix)]
            if len(prefix) >= 3:
                parts.append(prefix)
                parts.append(suffix)
                # Also try splitting the prefix further
                for pref2 in GERMAN_COMPOUND_PREFIXES:
                    if prefix.startswith(pref2) and len(prefix) > len(pref2) + 2:
                        parts.append(prefix[len(pref2):])
                        parts.append(pref2)
    
    # Deduplicate preserving order
    seen = set()
    unique = []
    for p in parts:
        if p not in seen and len(p) >= 4:
            seen.add(p)
            unique.append(p)
    return unique


# ──────────────────────────────────────────────────────────────────────
# Cross-language doctrinal term mapping (corpus-derived)
# ──────────────────────────────────────────────────────────────────────

# These mappings are derived from observing multilingual regestes in
# OpenCaseLaw decisions. They are deterministic and corpus-derived.
CROSS_LANG_DOCTRINAL = {
    # DE -> FR/IT
    "fürsorgepflicht": {"fr": "devoir d'assistance", "it": "obbligo di diligenza"},
    "kapitalverletzung": {"fr": "atteinte au capital", "it": "lesione del capitale"},
    "uberwachungspflicht": {"fr": "obligation de surveillance", "it": "obbligo di sorveglianza"},
    "treuepflicht": {"fr": "devoir de fidelite", "it": "dovere di fedelta"},
    "sorgfaltspflicht": {"fr": "obligation de diligence", "it": "obbligo di diligenza"},
    "haftung": {"fr": "responsabilite", "it": "responsabilita"},
    "verschulden": {"fr": "faute", "it": "colpa"},
    "kausalitat": {"fr": "causalite", "it": "causalita"},
    "adäquanz": {"fr": "adequation", "it": "adeguatezza"},
    "haftungsgrund": {"fr": "fondement de la responsabilite", "it": "fondamento della responsabilita"},
    "organisationspflicht": {"fr": "obligation d'organisation", "it": "obbligo di organizzazione"},
    "überwachung": {"fr": "surveillance", "it": "sorveglianza"},
    "kontrolle": {"fr": "controle", "it": "controllo"},
    "eigenschaft": {"fr": "qualite", "it": "qualita"},
    "stellung": {"fr": "position", "it": "posizione"},
    "befugnis": {"fr": "competence", "it": "competenza"},
    "zuständigkeit": {"fr": "competence", "it": "competenza"},
    "entscheidung": {"fr": "decision", "it": "decisione"},
    "urteil": {"fr": "arret", "it": "sentenza"},
    "beschwerde": {"fr": "recours", "it": "ricorso"},
    "rekurs": {"fr": "recours", "it": "ricorso"},
    "verfahren": {"fr": "procedure", "it": "procedimento"},
    "partei": {"fr": "partie", "it": "parte"},
    "kläger": {"fr": "demandeur", "it": "ricorrente"},
    "beklagter": {"fr": "defendeur", "it": "convenuto"},
    "arbeitsvertrag": {"fr": "contrat de travail", "it": "contratto di lavoro"},
    "arbeitgeber": {"fr": "employeur", "it": "datore di lavoro"},
    "arbeitnehmer": {"fr": "employe", "it": "lavoratore"},
    "kündigung": {"fr": "resiliation", "it": "licenziamento"},
    "auflösung": {"fr": "resolution", "it": "risoluzione"},
    "mietvertrag": {"fr": "bail", "it": "locazione"},
    "mieter": {"fr": "locataire", "it": "conduttore"},
    "vermieter": {"fr": "bailleur", "it": "locatore"},
    "mietzins": {"fr": "loyer", "it": "canone"},
    "zahlungsverzug": {"fr": "retard de paiement", "it": "ritardo di pagamento"},
    "frist": {"fr": "delai", "it": "termine"},
    "androhung": {"fr": "mise en demeure", "it": "intimazione"},
    "ausserordentlich": {"fr": "extraordinaire", "it": "straordinario"},
    "fristlos": {"fr": "sans delai", "it": "senza preavviso"},
    "missbrauch": {"fr": "abus", "it": "abuso"},
    "treu und glauben": {"fr": "bonne foi", "it": "buona fede"},
    "unbilligkeit": {"fr": "inequite", "it": "inequita"},
    "verhältnismässigkeit": {"fr": "proportionalite", "it": "proporzionalita"},
    "schutz": {"fr": "protection", "it": "protezione"},
    "persönlichkeit": {"fr": "personalite", "it": "personalita"},
    "gesundheit": {"fr": "sante", "it": "salute"},
    "sicherheit": {"fr": "securite", "it": "sicurezza"},
    "massnahme": {"fr": "mesure", "it": "misura"},
    "stand der technik": {"fr": "etat de la technique", "it": "stato della tecnica"},
    "zumutbar": {"fr": "exigible", "it": "esigibile"},
    "ganz": {"fr": "entier", "it": "intero"},
    "teil": {"fr": "partie", "it": "parte"},
    "ganze": {"fr": "entiere", "it": "intera"},
    "organ": {"fr": "organe", "it": "organo"},
    "geschäftsführung": {"fr": "gestion", "it": "gestione"},
    "verwaltung": {"fr": "administration", "it": "amministrazione"},
    "gesellschaft": {"fr": "societe", "it": "societa"},
    "aktiengesellschaft": {"fr": "societe anonyme", "it": "societa anonima"},
    "gmbh": {"fr": "sarl", "it": "sagl"},
    "stiftung": {"fr": "fondation", "it": "fondazione"},
    "verband": {"fr": "association", "it": "associazione"},
    "kapital": {"fr": "capital", "it": "capitale"},
    "vermögen": {"fr": "patrimoine", "it": "patrimonio"},
    "sacheinlage": {"fr": "apport en nature", "it": "conferimento in natura"},
    "schuldbrief": {"fr": "lettre de gage", "it": "cedola ipotecaria"},
    "eigentum": {"fr": "propriete", "it": "proprieta"},
    "besitz": {"fr": "possession", "it": "possesso"},
    "dinglich": {"fr": "reel", "it": "reale"},
    "obligatorisch": {"fr": "obligatoire", "it": "obbligatorio"},
    "vertrag": {"fr": "contrat", "it": "contratto"},
    "willkür": {"fr": "arbitraire", "it": "arbitrarieta"},
    "rechtsmissbrauch": {"fr": "abus de droit", "it": "abuso del diritto"},
    "rechtswidrig": {"fr": "illicite", "it": "illecito"},
    "widerrechtlich": {"fr": "illicite", "it": "illecito"},
    "schadensersatz": {"fr": "dommages-interets", "it": "risarcimento danni"},
    "genugtuung": {"fr": "reparation morale", "it": "riparazione morale"},
    "verletzung": {"fr": "violation", "it": "violazione"},
    "körperverletzung": {"fr": "lesions corporelles", "it": "lesioni corporali"},
    "gesundheitsschaden": {"fr": "atteinte a la sante", "it": "danno alla salute"},
    "ersatzpflicht": {"fr": "obligation de reparer", "it": "obbligo di risarcire"},
    "haftungsausschluss": {"fr": "exclusion de responsabilite", "it": "esclusione di responsabilita"},
    "haftungsbegrenzung": {"fr": "limitation de responsabilite", "it": "limitazione di responsabilita"},
    "ausschluss": {"fr": "exclusion", "it": "esclusione"},
    "begrenzung": {"fr": "limitation", "it": "limitazione"},
    "grenzziehung": {"fr": "delimitation", "it": "delimitazione"},
    "abgrenzung": {"fr": "delimitation", "it": "delimitazione"},
}

# Reverse mappings for FR/IT -> DE
def build_reverse_mappings():
    rev = {}
    for de_term, translations in CROSS_LANG_DOCTRINAL.items():
        for lang, term in translations.items():
            key = (lang, term)
            if key not in rev:
                rev[key] = []
            rev[key].append(de_term)
    return rev

REVERSE_CROSS_LANG = build_reverse_mappings()


# ──────────────────────────────────────────────────────────────────────
# Expansion term extraction from retrieved decisions
# ──────────────────────────────────────────────────────────────────────

def extract_expansion_terms(decisions: list[dict], query: str, max_terms: int = 20, under_covered_concepts: list[str] | None = None) -> list[str]:
    """
    Extract expansion terms from retrieved decisions' multilingual fields.
    
    Sources (in priority order):
    1. Cross-language equivalents of UNDER-COVERED concepts (highest priority)
    2. Cross-language equivalents of query concepts
    3. German compound splits of query/under-covered concepts
    4. Corpus-derived terms from retrieved decisions (frequency-ordered)
    
    Terms are filtered to legal concepts (length >= 5, not stopwords).
    """
    from product.query.concept_coverage import STOPWORDS, MIN_CONCEPT_CHARS
    
    # ─── PRIORITY 1: Cross-language equivalents for UNDER-COVERED concepts ───
    priority_terms = []
    if under_covered_concepts:
        for concept in under_covered_concepts:
            # Normalize the concept
            norm_concept = "".join(ch for ch in unicodedata.normalize("NFKD", concept) if not unicodedata.combining(ch)).casefold()
            # German compound splitting for under-covered concepts
            for part in split_german_compound(norm_concept):
                if part not in priority_terms and len(part) >= MIN_CONCEPT_CHARS:
                    priority_terms.append(part)
            # Cross-language mappings for under-covered concepts
            if norm_concept in CROSS_LANG_DOCTRINAL:
                for lang, term in CROSS_LANG_DOCTRINAL[norm_concept].items():
                    norm_term = "".join(ch for ch in unicodedata.normalize("NFKD", term) if not unicodedata.combining(ch)).casefold()
                    if norm_term not in priority_terms and len(norm_term) >= MIN_CONCEPT_CHARS:
                        priority_terms.append(norm_term)
            # Reverse mappings
            for lang in ["fr", "it"]:
                key = (lang, norm_concept)
                if key in REVERSE_CROSS_LANG:
                    for de_term in REVERSE_CROSS_LANG[key]:
                        norm_de = "".join(ch for ch in unicodedata.normalize("NFKD", de_term) if not unicodedata.combining(ch)).casefold()
                        if norm_de not in priority_terms and len(norm_de) >= MIN_CONCEPT_CHARS:
                            priority_terms.append(norm_de)
    
    # ─── PRIORITY 2: Cross-language equivalents of ALL query concepts ───
    query_concepts = []
    for raw in tokenize(query):
        tok = "".join(ch for ch in unicodedata.normalize("NFKD", raw) if not unicodedata.combining(ch))
        if len(tok) >= MIN_CONCEPT_CHARS and tok not in STOPWORDS:
            query_concepts.append(tok)
    
    for concept in query_concepts:
        # German compound splitting
        for part in split_german_compound(concept):
            if part not in priority_terms and len(part) >= MIN_CONCEPT_CHARS:
                priority_terms.append(part)
        # Cross-language mappings
        if concept in CROSS_LANG_DOCTRINAL:
            for lang, term in CROSS_LANG_DOCTRINAL[concept].items():
                norm_term = "".join(ch for ch in unicodedata.normalize("NFKD", term) if not unicodedata.combining(ch)).casefold()
                if norm_term not in priority_terms and len(norm_term) >= MIN_CONCEPT_CHARS:
                    priority_terms.append(norm_term)
        # Reverse mappings
        for lang in ["fr", "it"]:
            key = (lang, concept)
            if key in REVERSE_CROSS_LANG:
                for de_term in REVERSE_CROSS_LANG[key]:
                    norm_de = "".join(ch for ch in unicodedata.normalize("NFKD", de_term) if not unicodedata.combining(ch)).casefold()
                    if norm_de not in priority_terms and len(norm_de) >= MIN_CONCEPT_CHARS:
                        priority_terms.append(norm_de)
    
    # ─── PRIORITY 3: Corpus-derived terms from retrieved decisions ───
    corpus_terms = []
    all_text = []
    for d in decisions:
        for field in ["regeste", "title", "snippet", "citation_string_de", 
                      "citation_string_fr", "citation_string_it", "full_text"]:
            val = d.get(field)
            if val:
                all_text.append(str(val))
    
    if all_text:
        combined = " \n ".join(all_text)
        normalized = norm(combined)
        tokens = tokenize(normalized)
        
        candidates = []
        for token in tokens:
            if len(token) < MIN_CONCEPT_CHARS:
                continue
            if token in STOPWORDS:
                continue
            if token.isdigit():
                continue
            if not any(c.isalpha() for c in token):
                continue
            candidates.append(token)
        
        freq = {}
        for t in candidates:
            freq[t] = freq.get(t, 0) + 1
        
        sorted_terms = sorted(freq.keys(), key=lambda t: (-freq[t], t))
        corpus_terms = [t for t in sorted_terms if t not in priority_terms]
    
    # Combine: priority terms first, then corpus terms
    expanded = priority_terms + corpus_terms
    return expanded[:max_terms]


def build_expansion_variants(query: str, decisions: list[dict], max_variants: int = 5, under_covered_concepts: list[str] | None = None) -> list[str]:
    """
    Build deterministic query variants from expansion terms.
    
    Strategy:
    - Variant 0: original query (always first)
    - Variant 1: original + top DE expansion terms
    - Variant 2: original + top FR expansion terms (cross-lang)
    - Variant 3: original + top IT expansion terms (cross-lang)
    - Variant 4: original + norm tokens (statute references)
    """
    if max_variants < 1:
        return [query]
    
    expansion_terms = extract_expansion_terms(decisions, query, max_terms=30, under_covered_concepts=under_covered_concepts)
    
    # Categorize terms by language heuristic
    de_terms = []
    fr_terms = []
    it_terms = []
    norm_terms = []
    
    for term in expansion_terms:
        # Heuristic language detection
        if any(suffix in term for suffix in ["pflicht", "verletzung", "haftung", "klage", "gericht", 
                                              "entscheid", "urteil", "beschwerde", "verfahren",
                                              "arbeitgeber", "arbeitnehmer", "kündigung", "mietvertrag",
                                              "mieter", "vermieter", "zahlungsverzug", "fristlos",
                                              "missbrauch", "verhältnis", "schutz", "massnahme",
                                              "organ", "gesellschaft", "kapital", "eigentum",
                                              "vertrag", "schaden", "ersatz", "verletzung"]):
            de_terms.append(term)
        elif any(suffix in term for suffix in ["obligation", "responsabilite", "faute", "causalite",
                                                "employeur", "employe", "bailleur", "locataire",
                                                "loyer", "resiliation", "delai", "abus", "bonne foi",
                                                "proportionalite", "protection", "mesure", "technique",
                                                "exigible", "societe", "capital", "propriete", "contrat",
                                                "arbitraire", "dommages", "violation", "lesion", "reparation",
                                                "exclusion", "limitation", "delimitation"]):
            fr_terms.append(term)
        elif any(suffix in term for suffix in ["obbligo", "responsabilita", "colpa", "causalita",
                                                "datore", "lavoratore", "locatore", "conduttore",
                                                "canone", "risoluzione", "termini", "abuso", "buona fede",
                                                "proporzionalita", "protezione", "misura", "tecnica",
                                                "esigibile", "societa", "capitale", "proprieta", "contratto",
                                                "arbitrarieta", "danni", "violazione", "lesione", "riparazione",
                                                "esclusione", "limitazione", "delimitazione"]):
            it_terms.append(term)
        # Statute/norm tokens
        elif re.match(r"^(art|article|art\.)\s*\d+", term) or re.match(r"^\d+\s*(stgb|stpo|or|zgb|cpc|zpo|co|cp)$", term):
            norm_terms.append(term)
        else:
            # Default to DE for ambiguous
            de_terms.append(term)
    
    variants = [query]
    
    # Build variants by adding top terms from each category
    if len(variants) < max_variants and de_terms:
        variants.append(query + " " + " ".join(de_terms[:5]))
    if len(variants) < max_variants and fr_terms:
        variants.append(query + " " + " ".join(fr_terms[:5]))
    if len(variants) < max_variants and it_terms:
        variants.append(query + " " + " ".join(it_terms[:5]))
    if len(variants) < max_variants and norm_terms:
        variants.append(query + " " + " ".join(norm_terms[:5]))
    
    # Fill remaining slots with mixed top terms
    while len(variants) < max_variants:
        mixed = de_terms[:2] + fr_terms[:2] + it_terms[:1]
        if mixed:
            variants.append(query + " " + " ".join(mixed))
            # Remove used terms to avoid duplicate variants
            de_terms = de_terms[2:]
            fr_terms = fr_terms[2:]
            it_terms = it_terms[1:]
        else:
            break
    
    return variants[:max_variants]


# ──────────────────────────────────────────────────────────────────────
# Integration entry point
# ──────────────────────────────────────────────────────────────────────

def expand_query_bundle(bundle: dict, candidate_decisions: list[dict] | None = None) -> dict:
    """
    Apply query expansion to a bundle (additive, backwards-compatible).
    
    This is the drop-in integration point. It:
    1. Takes the existing bundle
    2. Measures baseline concept coverage to identify under-covered concepts
    3. Generates additional query_variants targeting those gaps
    4. Adds provenance entries documenting the expansion
    5. Returns a new bundle with expanded query_variants
    
    Does NOT modify: decisions, clusters, relations, geometry, answer, etc.
    """
    import copy
    from product.query.concept_coverage import coverage_report
    
    out = copy.deepcopy(bundle)
    query = out.get("query", "")
    
    # Use candidate decisions if available, else fall back to bundle decisions
    source_decisions = candidate_decisions or out.get("decisions", [])
    
    # Measure baseline coverage to identify under-covered concepts
    baseline_report = coverage_report(query, source_decisions)
    under_covered = baseline_report.get("under_covered", [])
    
    # Build expansion variants targeting under-covered concepts
    new_variants = build_expansion_variants(query, source_decisions, max_variants=5, under_covered_concepts=under_covered)
    
    # Merge with existing variants (preserve order, deduplicate)
    existing = list(out.get("query_variants") or [])
    seen = set(existing)
    for v in new_variants:
        if v not in seen:
            existing.append(v)
            seen.add(v)
    out["query_variants"] = existing
    
    # Add provenance entry
    prov = out.setdefault("provenance", {})
    prov["query_expansion"] = {
        "component": "frontier-query-concept-recall/v1",
        "method": "corpus_derived_multilingual_compound_crosslang_targeted",
        "added_variants": len(new_variants) - 1,  # minus original
        "total_variants": len(existing),
        "source_decision_count": len(source_decisions),
        "targeted_under_covered_concepts": under_covered,
        "claim_ceiling": (
            "expansion terms are derived from retrieved corpus multilingual fields and "
            "deterministic cross-language doctrinal mappings, prioritized for under-covered concepts; "
            "no generation, no paid APIs, no re-ranking or silent dropping of decisions"
        ),
    }
    
    return out


__all__ = [
    "norm", "tokenize", "split_german_compound", "CROSS_LANG_DOCTRINAL",
    "extract_expansion_terms", "build_expansion_variants", "expand_query_bundle",
]