"""
Multilingual Query Expansion
Expands Swiss legal queries across DE/FR/IT using legal terminology mappings.
"""
from typing import Dict, List, Set, Optional
from dataclasses import dataclass
import re


@dataclass
class ExpandedQuery:
    """Result of query expansion."""
    original: str
    variants: Dict[str, List[str]]  # language -> list of query variants
    all_terms: Set[str]
    expansion_notes: List[str]


# Core Swiss legal terminology mappings (DE -> FR -> IT)
# These are high-value legal term mappings for Swiss law
LEGAL_TERM_MAPPINGS = {
    # Contract law / Obligationenrecht
    "arbeitsvertrag": {
        "fr": ["contrat de travail", "contrat individuel de travail"],
        "it": ["contratto di lavoro", "contratto individuale di lavoro"],
    },
    "arbeitgeber": {
        "fr": ["employeur"],
        "it": ["datore di lavoro"],
    },
    "arbeitnehmer": {
        "fr": ["employé", "travailleur", "salarié"],
        "it": ["lavoratore", "dipendente"],
    },
    "kündigung": {
        "fr": ["résiliation", "licenciement", "congé"],
        "it": ["licenziamento", "risoluzione", "disdetta"],
    },
    "entlassung": {
        "fr": ["licenciement", "renvoi"],
        "it": ["licenziamento"],
    },
    "löhne": {
        "fr": ["salaires", "rémunération", "traitement"],
        "it": ["salari", "stipendi", "retribuzione"],
    },
    "lohn": {
        "fr": ["salaire", "rémunération"],
        "it": ["salario", "stipendio", "retribuzione"],
    },
    "bonus": {
        "fr": ["bonus", "gratification", "prime"],
        "it": ["bonus", "gratifica", "premio"],
    },
    "gratifikation": {
        "fr": ["gratification", "prime"],
        "it": ["gratifica"],
    },
    "überzeit": {
        "fr": ["heures supplémentaires", "heures suppl."],
        "it": ["ore straordinarie", "lavoro straordinario"],
    },
    "ferien": {
        "fr": ["vacances", "congés"],
        "it": ["ferie", "vacanze"],
    },
    
    # Civil procedure / ZPO
    "klage": {
        "fr": ["action", "demande", "procès"],
        "it": ["azione", "domanda", "causa"],
    },
    "beklagte": {
        "fr": ["défendeur", "intimé"],
        "it": ["convenuto", "resistente"],
    },
    "kläger": {
        "fr": ["demandeur", "requérant"],
        "it": ["attore", "ricorrente"],
    },
    "urteil": {
        "fr": ["jugement", "arrêt"],
        "it": ["sentenza", "decisione"],
    },
    "beschwerde": {
        "fr": ["recours", "appel"],
        "it": ["ricorso", "appello"],
    },
    "revision": {
        "fr": ["révision"],
        "it": ["revisione"],
    },
    
    # Corporate / Commercial
    "aktiengesellschaft": {
        "fr": ["société anonyme", "SA"],
        "it": ["società anonima", "SA"],
    },
    "gmbh": {
        "fr": ["société à responsabilité limitée", "Sàrl", "SARL"],
        "it": ["società a responsabilità limitata", "SaGL", "SRL"],
    },
    "geschäftsführer": {
        "fr": ["gérant", "directeur"],
        "it": ["gerente", "direttore"],
    },
    "aktionär": {
        "fr": ["actionnaire"],
        "it": ["azionista"],
    },
    "generalversammlung": {
        "fr": ["assemblée générale"],
        "it": ["assemblea generale"],
    },
    
    # Property / Tenancy
    "miete": {
        "fr": ["loyer", "bail"],
        "it": ["affitto", "locazione", "pigione"],
    },
    "mieter": {
        "fr": ["locataire"],
        "it": ["locatario", "inquilino"],
    },
    "vermieter": {
        "fr": ["bailleur", "propriétaire"],
        "it": ["locatore", "proprietario"],
    },
    "kündigungsschutz": {
        "fr": ["protection contre le licenciement", "protection contre la résiliation"],
        "it": ["protezione contro il licenziamento", "protezione contro la disdetta"],
    },
    
    # Constitutional / Administrative
    "grundrecht": {
        "fr": ["droit fondamental", "droit constitutionnel"],
        "it": ["diritto fondamentale", "diritto costituzionale"],
    },
    "verfassungsbeschwerde": {
        "fr": ["recours constitutionnel", "recours en matière constitutionnelle"],
        "it": ["ricorso costituzionale"],
    },
    "verhältnismässigkeit": {
        "fr": ["proportionnalité"],
        "it": ["proporzionalità"],
    },
    "willkür": {
        "fr": ["arbitraire"],
        "it": ["arbitrarietà"],
    },
    
    # Family law
    "scheidung": {
        "fr": ["divorce"],
        "it": ["divorzio"],
    },
    "unterhalt": {
        "fr": ["pension alimentaire", "contribution d'entretien"],
        "it": ["assegno di mantenimento", "contributo di mantenimento"],
    },
    "sorgerecht": {
        "fr": ["autorité parentale", "garde d'enfant"],
        "it": ["autorità parentale", "affidamento"],
    },
    
    # Criminal law
    "strafrecht": {
        "fr": ["droit pénal"],
        "it": ["diritto penale"],
    },
    "verbrechen": {
        "fr": ["crime"],
        "it": ["crimine"],
    },
    "vergehen": {
        "fr": ["délit"],
        "it": ["reato", "contravvenzione"],
    },
    "übertretung": {
        "fr": ["contravention"],
        "it": ["contravvenzione"],
    },
    "freiheitsstrafe": {
        "fr": ["peine privative de liberté", "emprisonnement"],
        "it": ["pena privativa della libertà", "reclusione"],
    },
    "geldstrafe": {
        "fr": ["amende", "peine pécuniaire"],
        "it": ["multa", "pena pecuniaria"],
    },
    
    # Legal concepts
    "treu und glauben": {
        "fr": ["bonne foi"],
        "it": ["buona fede"],
    },
    "missbrauch": {
        "fr": ["abus"],
        "it": ["abuso"],
    },
    "rechtsmissbrauch": {
        "fr": ["abus de droit"],
        "it": ["abuso del diritto"],
    },
    "schadenersatz": {
        "fr": ["dommages-intérêts", "réparation"],
        "it": ["risarcimento danni", "danni"],
    },
    "genugtuung": {
        "fr": ["réparation morale", "satisfaction"],
        "it": ["riparazione morale", "soddisfazione"],
    },
    "verjährung": {
        "fr": ["prescription"],
        "it": ["prescrizione"],
    },
    "verwirkung": {
        "fr": ["déchéance", "peremption"],
        "it": ["decadenza", "perenzione"],
    },
    "gutgläubigkeit": {
        "fr": ["bonne foi"],
        "it": ["buona fede"],
    },
    
    # Courts / Procedures
    "bundesgericht": {
        "fr": ["tribunal fédéral"],
        "it": ["tribunale federale"],
    },
    "obergericht": {
        "fr": ["cour d'appel", "tribunal cantonal"],
        "it": ["tribunale d'appello", "tribunale cantonale"],
    },
    "arbeitsgericht": {
        "fr": ["tribunal du travail", "conseil de prud'hommes"],
        "it": ["tribunale del lavoro"],
    },
    "zivilgericht": {
        "fr": ["tribunal civil"],
        "it": ["tribunale civile"],
    },
    "strafgericht": {
        "fr": ["tribunal pénal"],
        "it": ["tribunale penale"],
    },
    "verwaltungsgericht": {
        "fr": ["tribunal administratif"],
        "it": ["tribunale amministrativo"],
    },
}


# Common legal abbreviations and their expansions
LEGAL_ABBREVIATIONS = {
    "de": {
        "OR": "Obligationenrecht",
        "ZGB": "Zivilgesetzbuch",
        "ZPO": "Zivilprozessordnung",
        "StGB": "Strafgesetzbuch",
        "StPO": "Strafprozessordnung",
        "VG": "Verwaltungsgerichtsgesetz",
        "VwVG": "Verwaltungsverfahrensgesetz",
        "BGG": "Bundesgerichtsgesetz",
        "FusG": "Fusionsgesetz",
        "KartG": "Kartellgesetz",
        "UWG": "Bundesgesetz gegen den unlauteren Wettbewerb",
        "DSG": "Datenschutzgesetz",
        "BV": "Bundesverfassung",
    },
    "fr": {
        "CO": "Code des obligations",
        "CC": "Code civil",
        "CPC": "Code de procédure civile",
        "CP": "Code pénal",
        "CPP": "Code de procédure pénale",
        "LTAF": "Loi sur le Tribunal administratif fédéral",
        "LPA": "Loi sur la procédure administrative",
        "LTF": "Loi sur le Tribunal fédéral",
        "LFus": "Loi sur les fusions",
        "LCart": "Loi sur les cartels",
        "LCD": "Loi contre la concurrence déloyale",
        "LPD": "Loi sur la protection des données",
        "Cst": "Constitution fédérale",
    },
    "it": {
        "CO": "Codice delle obbligazioni",
        "CC": "Codice civile",
        "CPC": "Codice di procedura civile",
        "CP": "Codice penale",
        "CPP": "Codice di procedura penale",
        "LTAF": "Legge sul Tribunale amministrativo federale",
        "LPA": "Legge sulla procedura amministrativa",
        "LTF": "Legge sul Tribunale federale",
        "LFus": "Legge sulle fusioni",
        "LCart": "Legge sui cartelli",
        "LCD": "Legge contro la concorrenza sleale",
        "LPD": "Legge sulla protezione dei dati",
        "Cost": "Costituzione federale",
    },
}


# Legal area mappings for filtering
LEGAL_AREA_MAPPINGS = {
    "de": {
        "arbeitsrecht": "civil",
        "mietrecht": "civil",
        "vertragsrecht": "civil",
        "schadenersatzrecht": "civil",
        "erbrecht": "civil",
        "familienrecht": "civil",
        "gesellschaftsrecht": "civil",
        "strafrecht": "criminal",
        "verwaltungsrecht": "administrative",
        "verfassungsrecht": "constitutional",
        "steuerrecht": "tax",
        "sozialversicherungsrecht": "social_security",
        "geistiges_eigentum": "ip",
        "wettbewerbsrecht": "competition",
        "datenschutzrecht": "data_protection",
    },
    "fr": {
        "droit du travail": "civil",
        "droit du bail": "civil",
        "droit des contrats": "civil",
        "droit de la responsabilité": "civil",
        "droit des successions": "civil",
        "droit de la famille": "civil",
        "droit des sociétés": "civil",
        "droit pénal": "criminal",
        "droit administratif": "administrative",
        "droit constitutionnel": "constitutional",
        "droit fiscal": "tax",
        "droit des assurances sociales": "social_security",
        "propriété intellectuelle": "ip",
        "droit de la concurrence": "competition",
        "protection des données": "data_protection",
    },
    "it": {
        "diritto del lavoro": "civil",
        "diritto di locazione": "civil",
        "diritto dei contratti": "civil",
        "diritto della responsabilità": "civil",
        "diritto successorio": "civil",
        "diritto di famiglia": "civil",
        "diritto societario": "civil",
        "diritto penale": "criminal",
        "diritto amministrativo": "administrative",
        "diritto costituzionale": "constitutional",
        "diritto tributario": "tax",
        "diritto delle assicurazioni sociali": "social_security",
        "proprietà intellettuale": "ip",
        "diritto della concorrenza": "competition",
        "protezione dei dati": "data_protection",
    },
}


def expand_query(query: str, languages: Optional[List[str]] = None) -> ExpandedQuery:
    """
    Expand a legal query across DE/FR/IT using terminology mappings.
    
    Args:
        query: Original query string (assumed to be in any language)
        languages: Target languages (default: ["de", "fr", "it"])
    
    Returns:
        ExpandedQuery with variants per language
    """
    if languages is None:
        languages = ["de", "fr", "it"]
    
    query_lower = query.lower()
    variants = {lang: [query] for lang in languages}
    all_terms = set(query_lower.split())
    notes = []
    
    # Find matching legal terms and expand
    for de_term, translations in LEGAL_TERM_MAPPINGS.items():
        if de_term in query_lower:
            fr_terms = translations.get("fr", [])
            it_terms = translations.get("it", [])
            
            if "fr" in languages and fr_terms:
                # Create FR variant by replacing DE term with FR term
                for fr_term in fr_terms:
                    fr_variant = query_lower.replace(de_term, fr_term)
                    if fr_variant not in variants["fr"]:
                        variants["fr"].append(fr_variant)
                        all_terms.add(fr_term)
                notes.append(f"Expanded '{de_term}' -> FR: {', '.join(fr_terms)}")
            
            if "it" in languages and it_terms:
                for it_term in it_terms:
                    it_variant = query_lower.replace(de_term, it_term)
                    if it_variant not in variants["it"]:
                        variants["it"].append(it_variant)
                        all_terms.add(it_term)
                notes.append(f"Expanded '{de_term}' -> IT: {', '.join(it_terms)}")
    
    # Also check FR terms in query
    for de_term, translations in LEGAL_TERM_MAPPINGS.items():
        fr_terms = translations.get("fr", [])
        it_terms = translations.get("it", [])
        
        for fr_term in fr_terms:
            if fr_term in query_lower:
                if "de" in languages and de_term not in query_lower:
                    de_variant = query_lower.replace(fr_term, de_term)
                    if de_variant not in variants["de"]:
                        variants["de"].append(de_variant)
                        all_terms.add(de_term)
                if "it" in languages and it_terms:
                    for it_term in it_terms:
                        it_variant = query_lower.replace(fr_term, it_term)
                        if it_variant not in variants["it"]:
                            variants["it"].append(it_variant)
                            all_terms.add(it_term)
        
        for it_term in it_terms:
            if it_term in query_lower:
                if "de" in languages and de_term not in query_lower:
                    de_variant = query_lower.replace(it_term, de_term)
                    if de_variant not in variants["de"]:
                        variants["de"].append(de_variant)
                        all_terms.add(de_term)
                if "fr" in languages and fr_terms:
                    for fr_term in fr_terms:
                        fr_variant = query_lower.replace(it_term, fr_term)
                        if fr_variant not in variants["fr"]:
                            variants["fr"].append(fr_variant)
                            all_terms.add(fr_term)
    
    # Expand abbreviations
    for lang in languages:
        if lang in LEGAL_ABBREVIATIONS:
            for abbr, full in LEGAL_ABBREVIATIONS[lang].items():
                if abbr.lower() in query_lower:
                    expanded = query_lower.replace(abbr.lower(), full.lower())
                    if expanded not in variants[lang]:
                        variants[lang].append(expanded)
                        all_terms.add(full.lower())
                    notes.append(f"Expanded abbreviation '{abbr}' -> '{full}' ({lang})")
    
    # Deduplicate variants per language
    for lang in variants:
        seen = set()
        unique = []
        for v in variants[lang]:
            if v not in seen:
                seen.add(v)
                unique.append(v)
        variants[lang] = unique
    
    return ExpandedQuery(
        original=query,
        variants=variants,
        all_terms=all_terms,
        expansion_notes=notes,
    )


def get_legal_area_filter(query: str, language: str = "de") -> Optional[str]:
    """Extract legal area filter from query based on terminology."""
    query_lower = query.lower()
    mappings = LEGAL_AREA_MAPPINGS.get(language, {})
    
    for term, area in mappings.items():
        if term in query_lower:
            return area
    return None


def build_multilingual_search_queries(
    query: str,
    languages: Optional[List[str]] = None,
    max_variants_per_lang: int = 3,
) -> Dict[str, List[str]]:
    """
    Build optimized search queries for each language.
    
    Returns dict: language -> list of query strings to execute
    """
    expanded = expand_query(query, languages)
    
    # Limit variants per language
    result = {}
    for lang, variant_list in expanded.variants.items():
        result[lang] = variant_list[:max_variants_per_lang]
    
    return result


def detect_query_language(query: str) -> str:
    """Heuristically detect the language of a query."""
    query_lower = query.lower()
    
    # Count matches per language
    scores = {"de": 0, "fr": 0, "it": 0}
    
    for de_term, translations in LEGAL_TERM_MAPPINGS.items():
        if de_term in query_lower:
            scores["de"] += 2
        for fr_term in translations.get("fr", []):
            if fr_term in query_lower:
                scores["fr"] += 2
        for it_term in translations.get("it", []):
            if it_term in query_lower:
                scores["it"] += 2
    
    # Check abbreviations
    for lang, abbrs in LEGAL_ABBREVIATIONS.items():
        for abbr in abbrs:
            if abbr.lower() in query_lower:
                scores[lang] += 1
    
    # Return language with highest score, default to German
    return max(scores, key=scores.get) if max(scores.values()) > 0 else "de"