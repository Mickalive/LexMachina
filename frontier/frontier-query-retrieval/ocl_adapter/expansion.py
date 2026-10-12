"""
Multilingual query expansion for Swiss legal research.

Provides DE/FR/IT synonym expansion for Swiss legal terminology to improve
cross-language recall when searching OpenCaseLaw.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from collections import OrderedDict

# Swiss legal term synonyms across German, French, Italian
# Based on Swiss legal vocabulary: OR, ZGB, SchKG, BGG, StPO, etc.
SWISS_LEGAL_SYNONYMS: Dict[str, Dict[str, List[str]]] = {
    # Contract / Obligation law (OR)
    "vertrag": {
        "de": ["vertrag", "verträge", "vertragsrecht", "obligationenrecht"],
        "fr": ["contrat", "contrats", "droit des obligations", "obligations"],
        "it": ["contratto", "contratti", "diritto delle obbligazioni", "obbligazioni"],
    },
    "miete": {
        "de": ["miete", "mietrecht", "mietvertrag", "mietzins", "erstreckung", "kündigung", "anfechtung"],
        "fr": ["loyer", "bail", "droit du bail", "prolongation", "congés", "contestation"],
        "it": ["affitto", "locazione", "diritto della locazione", "proroga", "disdetta", "impugnazione"],
    },
    "kauf": {
        "de": ["kauf", "kaufvertrag", "kaufrecht", "gewährleistung", "wandelung", "minderung"],
        "fr": ["vente", "contrat de vente", "garantie", "résolution", "réduction"],
        "it": ["vendita", "contratto di vendita", "garanzia", "risoluzione", "riduzione"],
    },
    "arbeit": {
        "de": ["arbeit", "arbeitsrecht", "arbeitsvertrag", "kündigung", "entlassung", "ferien", "lohn", "überzeit"],
        "fr": ["travail", "droit du travail", "contrat de travail", "licenciement", "congés", "salaire", "heures supplémentaires"],
        "it": ["lavoro", "diritto del lavoro", "contratto di lavoro", "licenziamento", "ferie", "salario", "straordinari"],
    },
    
    # Tort / Liability law
    "haftung": {
        "de": ["haftung", "schadenersatz", "unerlaubte handlung", "verschulden", "kausalität", "adäquanz"],
        "fr": ["responsabilité", "dommages-intérêts", "fait illicite", "faute", "causalité", "adéquation"],
        "it": ["responsabilità", "risarcimento", "fatto illecito", "colpa", "causalità", "adeguatezza"],
    },
    "unfall": {
        "de": ["unfall", "unfallversicherung", "uvg", "berufsunfall", "freizeitunfall"],
        "fr": ["accident", "assurance-accidents", "laa", "accident professionnel", "accident non professionnel"],
        "it": ["infortunio", "assicurazione infortuni", "lainf", "infortunio professionale", "infortunio non professionale"],
    },
    
    # Family law
    "scheidung": {
        "de": ["scheidung", "ehe", "ehescheidung", "unterhalt", "nachehelicher unterhalt", "kinder", "sorgerecht", "elternschaft"],
        "fr": ["divorce", "mariage", "pension", "contribution d'entretien", "enfants", "autorité parentale", "garde"],
        "it": ["divorzio", "matrimonio", "assegno", "contributo di mantenimento", "figli", "autorità parentale", "affidamento"],
    },
    "ehe": {
        "de": ["ehe", "eheschliessung", "ehevertrag", "güterrecht", "errungenschaftsbeteiligung", "gütertrennung", "gütergemeinschaft"],
        "fr": ["mariage", "célébration du mariage", "contrat de mariage", "régime matrimonial", "participation aux acquêts", "séparation de biens", "communauté de biens"],
        "it": ["matrimonio", "celebrazione del matrimonio", "contratto di matrimonio", "regime matrimoniale", "partecipazione agli acquisti", "separazione dei beni", "comunione dei beni"],
    },
    
    # Inheritance law
    "erbschaft": {
        "de": ["erbschaft", "erbrecht", "testament", "erbvertrag", "pflichtteil", "enterbung", "nachlass", "erben"],
        "fr": ["succession", "droit successoral", "testament", "pacte successoral", "réserve héréditaire", "déshéritance", "héritage", "héritiers"],
        "it": ["successione", "diritto successorio", "testamento", "patto successorio", "legittima", "diseredazione", "eredità", "eredi"],
    },
    
    # Property law
    "eigentum": {
        "de": ["eigentum", "eigentumsrecht", "sachenrecht", "grundbuch", "dienstbarkeit", "grundpfandrecht", "hypothek"],
        "fr": ["propriété", "droit de propriété", "droit des biens", "registre foncier", "servitude", "droit de gage immobilier", "hypothèque"],
        "it": ["proprietà", "diritto di proprietà", "diritto dei beni", "registro fondiario", "servitù", "pegno immobiliare", "ipoteca"],
    },
    
    # Criminal law
    "strafrecht": {
        "de": ["strafrecht", "strafe", "verbrechen", "vergehen", "übertretung", "strafgesetzbuch", "stgb", "vorsatz", "fahrlässigkeit"],
        "fr": ["droit pénal", "peine", "crime", "délit", "contravention", "code pénal", "cp", "intention", "négligence"],
        "it": ["diritto penale", "pena", "crimine", "delitto", "contravvenzione", "codice penale", "cp", "dolo", "colpa"],
    },
    
    # Administrative / Constitutional law
    "verwaltungsrecht": {
        "de": ["verwaltungsrecht", "verwaltung", "verfügung", "beschwerde", "revisionsrecht", "grundrechte", "bv"],
        "fr": ["droit administratif", "administration", "décision", "recours", "droit de révision", "droits fondamentaux", "cst"],
        "it": ["diritto amministrativo", "amministrazione", "decisione", "ricorso", "diritto di revisione", "diritti fondamentali", "cost"],
    },
    "asyl": {
        "de": ["asyl", "asylrecht", "flüchtling", "asylverfahren", "abweisung", "nichtzurückweisung", "humanitäres aufenthaltsrecht"],
        "fr": ["asile", "droit d'asile", "réfugié", "procédure d'asile", "renvoi", "non-refoulement", "séjour humanitaire"],
        "it": ["asilo", "diritto d'asilo", "rifugiato", "procedura d'asilo", "rinvio", "non-refoulement", "soggiorno umanitario"],
    },
    
    # Social security
    "sozialversicherung": {
        "de": ["sozialversicherung", "ahv", "iv", "bvg", "uvg", "faq", "el", "ergänzungsleistungen", "invalidität", "rente"],
        "fr": ["assurance sociale", "avs", "ai", "lpp", "laa", "apg", "pc", "prestations complémentaires", "invalidité", "rente"],
        "it": ["assicurazione sociale", "avs", "ai", "lpp", "lainf", "ipg", "pc", "prestazioni complementari", "invalidità", "rendita"],
    },
    
    # Tax law
    "steuer": {
        "de": ["steuer", "steuerrecht", "direkte steuer", "mehrwertsteuer", "stempelsteuer", "veranlagung", "steuererklärung"],
        "fr": ["impôt", "droit fiscal", "impôt direct", "tva", "droit de timbre", "taxation", "déclaration d'impôt"],
        "it": ["imposta", "diritto tributario", "imposta diretta", "iva", "imposta di bollo", "tassazione", "dichiarazione d'imposta"],
    },
    
    # Procedural law
    "verfahren": {
        "de": ["verfahren", "prozess", "klage", "beklagter", "kläger", "gericht", "entscheid", "urteil", "beschluss", "verfügung"],
        "fr": ["procédure", "procès", "demande", "défendeur", "demandeur", "tribunal", "décision", "jugement", "arrêt", "ordonnance"],
        "it": ["procedimento", "processo", "domanda", "convenuto", "attore", "tribunale", "decisione", "sentenza", "decreto", "ordinanza"],
    },
    "beschwerde": {
        "de": ["beschwerde", "revision", "berufung", "rekurs", "nichtigkeitsbeschwerde", "verfassungsbeschwerde", "bgg"],
        "fr": ["recours", "révision", "appel", "recours en nullité", "recours constitutionnel", "lttf"],
        "it": ["ricorso", "revisione", "appello", "ricorso per nullità", "ricorso costituzionale", "lttf"],
    },
    
    # Corporate / Commercial law
    "gesellschaft": {
        "de": ["gesellschaft", "ag", "gmbh", "kollektivgesellschaft", "kommanditgesellschaft", "einzelfirma", "handelsregister"],
        "fr": ["société", "sa", "sàrl", "société en nom collectif", "société en commandite", "entreprise individuelle", "registre du commerce"],
        "it": ["società", "sa", "sagl", "società in nome collettivo", "società in accomandita", "impresa individuale", "registro di commercio"],
    },
    
    # Intellectual property
    "geistiges eigentum": {
        "de": ["geistiges eigentum", "urheberrecht", "patentrecht", "markenrecht", "designrecht", "wettbewerbsrecht", "ug"],
        "fr": ["propriété intellectuelle", "droit d'auteur", "droit des brevets", "droit des marques", "droit des dessins", "droit de la concurrence", "lcd"],
        "it": ["proprietà intellettuale", "diritto d'autore", "diritto dei brevetti", "diritto dei marchi", "diritto dei disegni", "diritto della concorrenza", "lcd"],
    },
    
    # Data protection
    "datenschutz": {
        "de": ["datenschutz", "dsg", "personendaten", "einwilligung", "datenbearbeitung", "auskunftsrecht", "löschungsrecht"],
        "fr": ["protection des données", "lpd", "données personnelles", "consentement", "traitement de données", "droit d'accès", "droit à l'effacement"],
        "it": ["protezione dei dati", "lpd", "dati personali", "consenso", "trattamento dati", "diritto d'accesso", "diritto alla cancellazione"],
    },
}

# Language detection patterns - use common legal terms as indicators
LANGUAGE_PATTERNS = {
    "de": re.compile(r"\b(und|oder|der|die|das|von|zu|mit|für|auf|ein|eine|einen|dem|den|des|ist|sind|wird|wurde|hat|haben|recht|gesetz|vertrag|klage|gericht|entscheid|artikel|absatz|satz)\b", re.IGNORECASE),
    "fr": re.compile(r"\b(et|ou|le|la|les|de|à|pour|sur|un|une|du|des|est|sont|sera|était|a|ont|droit|loi|contrat|procès|tribunal|décision|article|alinéa)\b", re.IGNORECASE),
    "it": re.compile(r"\b(e|o|il|la|lo|gli|le|di|a|per|su|un|una|del|dei|della|è|sono|sarà|era|ha|hanno|diritto|legge|contratto|processo|tribunale|decisione|articolo|comma)\b", re.IGNORECASE),
}

# Fallback: detect by legal term vocabulary
LANGUAGE_VOCAB = {
    "de": {"vertrag", "klage", "gericht", "entscheid", "artikel", "absatz", "recht", "gesetz", "miete", "kündigung", "scheidung", "erbschaft", "haftung", "strafe", "asyl", "steuer", "beschwerde", "gesellschaft", "datenschutz", "verfahren", "urteil", "beklagter", "kläger", "arbeit", "arbeitsrecht", "lohn", "ferien", "entlassung", "mietrecht", "erstreckung"},
    "fr": {"contrat", "procès", "tribunal", "décision", "article", "alinéa", "droit", "loi", "bail", "congé", "divorce", "succession", "responsabilité", "peine", "asile", "impôt", "recours", "société", "données", "procédure", "jugement", "défendeur", "demandeur", "travail", "licenciement", "salaire", "congés", "droit du travail"},
    "it": {"contratto", "processo", "tribunale", "decisione", "articolo", "comma", "diritto", "legge", "affitto", "disdetta", "divorzio", "successione", "responsabilità", "pena", "asilo", "imposta", "ricorso", "società", "dati", "procedimento", "sentenza", "convenuto", "attore", "lavoro", "licenziamento", "salario", "ferie", "diritto del lavoro", "straordinari"},
}


@dataclass
class ExpansionResult:
    """Result of query expansion with provenance."""
    original_query: str
    expanded_terms: Dict[str, List[str]]  # language -> terms
    combined_query: str
    language_detected: Optional[str]
    variants: List[str]  # Query variants for multi-query search
    
    def to_dict(self) -> Dict:
        return {
            "original_query": self.original_query,
            "expanded_terms": self.expanded_terms,
            "combined_query": self.combined_query,
            "language_detected": self.language_detected,
            "variants": self.variants,
        }


class QueryExpander:
    """
    Multilingual query expander for Swiss legal queries.
    
    Expands a query with synonyms in DE/FR/IT to improve cross-language recall.
    Preserves provenance by tracking which terms came from expansion vs original.
    """
    
    def __init__(
        self,
        synonyms: Optional[Dict[str, Dict[str, List[str]]]] = None,
        max_expansion_terms: int = 12,
        max_variants: int = 4,
    ):
        self.synonyms = synonyms or SWISS_LEGAL_SYNONYMS
        self.max_expansion_terms = max_expansion_terms
        self.max_variants = max_variants
    
    def detect_language(self, text: str) -> Optional[str]:
        """Detect the primary language of a query text."""
        scores = {}
        text_lower = text.lower()
        tokens = set(self.tokenize(text))
        
        # Method 1: Pattern matching for common words
        for lang, pattern in LANGUAGE_PATTERNS.items():
            matches = len(pattern.findall(text))
            scores[lang] = matches * 2  # Weight patterns higher
        
        # Method 2: Legal vocabulary matching
        for lang, vocab in LANGUAGE_VOCAB.items():
            vocab_matches = len(tokens & vocab)
            scores[lang] = scores.get(lang, 0) + vocab_matches
        
        if max(scores.values()) > 0:
            return max(scores, key=scores.get)
        return None
    
    def tokenize(self, text: str) -> List[str]:
        """Tokenize query into words (preserves compound terms)."""
        # Swiss legal terms often have hyphens, numbers, special chars
        tokens = re.findall(r"[A-Za-zÄÖÜäöüÉÈÊàèéêïîôùûçÀÈÉÊÏÎÔÙÛÇ0-9\-\.]+", text)
        return [t.lower() for t in tokens if len(t) > 1]
    
    def expand_token(self, token: str) -> Dict[str, List[str]]:
        """Expand a single token into multilingual synonyms."""
        token_lower = token.lower()
        result = {"de": [], "fr": [], "it": []}
        
        # Direct match in synonyms
        if token_lower in self.synonyms:
            for lang, terms in self.synonyms[token_lower].items():
                result[lang].extend(terms)
        
        # Also check if token appears in any synonym list (reverse lookup)
        for key, lang_dict in self.synonyms.items():
            for lang, terms in lang_dict.items():
                if token_lower in [t.lower() for t in terms]:
                    for l, ts in lang_dict.items():
                        result[l].extend(ts)
        
        # Deduplicate
        for lang in result:
            seen = set()
            unique = []
            for term in result[lang]:
                if term.lower() not in seen:
                    seen.add(term.lower())
                    unique.append(term)
            result[lang] = unique
        
        return result
    
    def expand_query(self, query: str) -> ExpansionResult:
        """
        Expand a query with multilingual synonyms.
        
        Returns ExpansionResult with:
        - expanded_terms: dict mapping language to list of expanded terms
        - combined_query: original query + top expansion terms
        - variants: list of query variants for multi-query search
        """
        tokens = self.tokenize(query)
        language = self.detect_language(query)
        
        # Collect all expansions
        all_expansions: Dict[str, Set[str]] = {"de": set(), "fr": set(), "it": set()}
        
        for token in tokens:
            expansions = self.expand_token(token)
            for lang, terms in expansions.items():
                all_expansions[lang].update(terms)
        
        # Remove original tokens from expansions
        original_lower = {t.lower() for t in tokens}
        for lang in all_expansions:
            all_expansions[lang] = [t for t in all_expansions[lang] if t.lower() not in original_lower]
        
        # Convert to lists, limit per language
        expanded_terms = {}
        for lang in ("de", "fr", "it"):
            expanded_terms[lang] = list(all_expansions[lang])[:self.max_expansion_terms]
        
        # Build combined query (original + top terms from all languages)
        all_extra = []
        for lang in ("de", "fr", "it"):
            all_extra.extend(expanded_terms[lang][:4])  # Top 4 per language
        
        # Deduplicate extra terms
        seen_extra = set()
        unique_extra = []
        for term in all_extra:
            if term.lower() not in seen_extra:
                seen_extra.add(term.lower())
                unique_extra.append(term)
        
        combined_query = query
        if unique_extra:
            combined_query = query + " " + " ".join(unique_extra[:self.max_expansion_terms])
        
        # Build query variants for multi-query search
        variants = [query]  # Always include original
        
        # Variant 1: Combined (all languages)
        if unique_extra:
            variants.append(combined_query)
        
        # Variant 2: Per-language focused
        for lang in ("de", "fr", "it"):
            lang_terms = expanded_terms[lang][:6]
            if lang_terms:
                variants.append(query + " " + " ".join(lang_terms))
        
        # Limit variants
        variants = variants[:self.max_variants]
        
        return ExpansionResult(
            original_query=query,
            expanded_terms={k: list(v) for k, v in all_expansions.items()},
            combined_query=combined_query,
            language_detected=language,
            variants=variants,
        )
    
    def expand_for_search(self, query: str) -> List[str]:
        """
        Get query variants optimized for search API.
        
        Returns list of query strings to execute sequentially.
        """
        result = self.expand_query(query)
        return result.variants


def expand_query(query: str, max_terms: int = 12) -> ExpansionResult:
    """Convenience function for single query expansion."""
    expander = QueryExpander(max_expansion_terms=max_terms)
    return expander.expand_query(query)


def get_search_variants(query: str, max_variants: int = 4) -> List[str]:
    """Get search-optimized query variants."""
    expander = QueryExpander(max_variants=max_variants)
    return expander.expand_for_search(query)