"""
Statute extraction from full_text via regex patterns.
Addresses the known limitation that cited_laws is null from the OpenCaseLaw API.

Swiss legal citations follow patterns like:
- Art. 41 OR
- Art. 8 ZGB
- Art. 3 Abs. 2 lit. a StPO
- Art. 176 StGB
- Art. 55 ZPO
- SR 220 (referring to Swiss Compilation of Legislation)
"""
import re
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass


@dataclass
class StatuteReference:
    """Extracted statute reference."""
    article: str          # e.g., "Art. 41"
    law_abbrev: str       # e.g., "OR", "ZGB", "StPO"
    sr_number: Optional[str] = None  # e.g., "220"
    context: Optional[str] = None    # surrounding text snippet
    position: Optional[int] = None   # character position in text


# Common Swiss law abbreviations
SWISS_LAW_ABBREVS = {
    # Zivilrecht
    "OR": "Obligationenrecht",
    "ZGB": "Zivilgesetzbuch",
    "ZPO": "Zivilprozessordnung",
    "SchKG": "Schuldbetreibungs- und Konkursgesetz",
    "USG": "Umweltschutzgesetz",
    "SVG": "Strassenverkehrsgesetz",
    "UWG": "Ugesetz gegen den unlauteren Wettbewerb",
    "MSchG": "Markenschutzgesetz",
    "UrhG": "Urheberrechtsgesetz",
    "PatG": "Patentgesetz",
    "KSchG": "Konsumentenschutzgesetz",
    "VVG": "Versicherungsvertragsgesetz",
    
    # Strafrecht
    "StGB": "Strafgesetzbuch",
    "StPO": "Strafprozessordnung",
    "JStG": "Jugendstrafgesetz",
    "BtMG": "Betäubungsmittelgesetz",
    "WG": "Waffengesetz",
    
    # Öffentliches Recht
    "BGG": "Bundesgerichtsgesetz",
    "VwVG": "Verwaltungsverfahrensgesetz",
    "VwGO": "Verwaltungsgerichtsordnung",
    "VprG": "Verwaltungsprinzipiengesetz",
    "RPG": "Raumplanungsgesetz",
    "Bundesverfassung": "Bundesverfassung",
    "BV": "Bundesverfassung",
    "VG": "Verwaltungsgesetz",
    "EG": "Einführungsgesetz",
    "StG": "Steuergesetz",
    "VAG": "Versicherungsaufsichtsgesetz",
    "BankG": "Bankengesetz",
    "FinIA": "Finanzdienstleistungsgesetz",
    "FIDLEG": "Finanzdienstleistungsgesetz",
    "FinIG": "Finanzmarktinfrastrukturgesetz",
    
    # Sozialversicherungsrecht
    "AVG": "Alters- und Hinterlassenenversicherungsgesetz",
    "AHVG": "Alters- und Hinterlassenenversicherungsgesetz",
    "IVG": "Invalidenversicherungsgesetz",
    "UVG": "Unfallversicherungsgesetz",
    "VGK": "Verwaltungsgerichtskreis",
    "VSKG": "Sozialversicherungsrecht",
    "ArG": "Arbeitslosenversicherungsgesetz",
    "VG": "Verwaltungsgesetz",
    
    # Zivilstandsrecht
    "ZStV": "Zivilstandsgesetz",
    
    # Internationales Recht
    "IPRG": "Internationales Privatrechtsgesetz",
    "LUG": "Lugano-Übereinkommen",
    "Hague": "Haager Übereinkommen",
}

# Primary regex: Art. <number> [Abs. <number>] [lit. <letter>] <LAW_ABBREV>
ARTICLE_PATTERN = re.compile(
    r'Art\.\s*(\d+(?:\s*(?:bis|–|-)\s*\d+)?)'  # Article number(s)
    r'(?:\s*Abs\.\s*(\d+(?:\s*(?:bis|–|-)\s*\d+)?))?'  # Optional Absatz
    r'(?:\s*lit\.\s*([a-z]))?'  # Optional lit.
    r'\s+([A-ZÄÖÜ][A-Za-zÄÖÜäöü]{1,30})'  # Law abbreviation (uppercase start)
    r'(?:\s*,\s*\d+\.\s*Absatz)?'  # Optional additional Absatz reference
)

# Secondary pattern: SR <number> references
SR_PATTERN = re.compile(r'SR\s+(\d{1,5}(?:\.\d+)*)')

# Tertiary pattern: Law name without Art. prefix (e.g., "laut OR Art. 41")
LAW_NAME_PATTERN = re.compile(
    r'\b([A-ZÄÖÜ][A-Za-zÄÖÜäöü]{1,30})\s+Art\.\s*(\d+)'
)


def extract_statutes_from_text(
    text: str,
    max_results: int = 500,
    include_context: bool = False,
    context_chars: int = 40
) -> List[StatuteReference]:
    """
    Extract statute references from Swiss court decision text.
    
    Args:
        text: Full text of the decision
        max_results: Maximum number of references to return
        include_context: Whether to include surrounding text snippets
        context_chars: Number of characters of context around each match
    
    Returns:
        List of StatuteReference objects
    """
    if not text:
        return []
    
    references = []
    seen = set()  # Deduplicate by (article, law)
    
    # Primary pattern: Art. X [Abs. Y] [lit. Z] LAW
    for match in ARTICLE_PATTERN.finditer(text):
        if len(references) >= max_results:
            break
        
        article_num = match.group(1).strip()
        absatz = match.group(2)
        lit = match.group(3)
        law = match.group(4)
        
        # Skip common false positives
        if law in ("Der", "Die", "Das", "Ein", "Eine", "Bei", "Nach", "Vor", "Aus", 
                    "Über", "Für", "Gegen", "Zwischen", "An", "Auf", "In", "Zu",
                    "Bundes", "Obergericht", "Kantonsgericht", "Bezirksgericht",
                    "Stadtgericht", "Gemeinde", "Kanton", "Schweiz",
                    "Gemäss", "Entsprechend", "Zufolge", "Kraft", "Laut",
                    "Massgabe", "Sinne", "Gesetz", "Gericht", "Recht",
                    "Statt", "Anwendbar", "Begründet", "Beruht", "Erfordert"):
            continue
        
        article_str = f"Art. {article_num}"
        if absatz:
            article_str += f" Abs. {absatz}"
        if lit:
            article_str += f" lit. {lit}"
        
        key = (article_str, law)
        if key in seen:
            continue
        seen.add(key)
        
        ref = StatuteReference(
            article=article_str,
            law_abbrev=law,
            position=match.start(),
        )
        
        if include_context:
            start = max(0, match.start() - context_chars)
            end = min(len(text), match.end() + context_chars)
            ref.context = text[start:end].replace('\n', ' ')
        
        references.append(ref)
    
    # Secondary pattern: Law Art. X (reversed order)
    for match in LAW_NAME_PATTERN.finditer(text):
        if len(references) >= max_results:
            break
        
        law = match.group(1)
        article_num = match.group(2)
        
        if law in ("Der", "Die", "Das", "Ein", "Eine", "Bei", "Nach", "Vor", "Aus",
                    "Über", "Für", "Gegen", "Zwischen", "An", "Auf", "In", "Zu",
                    "Bundes", "Obergericht", "Kantonsgericht", "Bezirksgericht"):
            continue
        
        article_str = f"Art. {article_num}"
        key = (article_str, law)
        if key in seen:
            continue
        seen.add(key)
        
        ref = StatuteReference(
            article=article_str,
            law_abbrev=law,
            position=match.start(),
        )
        
        if include_context:
            start = max(0, match.start() - context_chars)
            end = min(len(text), match.end() + context_chars)
            ref.context = text[start:end].replace('\n', ' ')
        
        references.append(ref)
    
    # SR references
    for match in SR_PATTERN.finditer(text):
        if len(references) >= max_results:
            break
        
        sr_num = match.group(1)
        key = (f"SR {sr_num}", "SR")
        if key in seen:
            continue
        seen.add(key)
        
        ref = StatuteReference(
            article=f"SR {sr_num}",
            law_abbrev="SR",
            sr_number=sr_num,
            position=match.start(),
        )
        
        if include_context:
            start = max(0, match.start() - context_chars)
            end = min(len(text), match.end() + context_chars)
            ref.context = text[start:end].replace('\n', ' ')
        
        references.append(ref)
    
    return references


def extract_statutes_batch(
    decisions: List[Dict[str, Any]],
    max_per_decision: int = 200
) -> Dict[str, List[str]]:
    """
    Extract statutes from a batch of canonical decisions.
    Returns dict of decision_id -> list of "Art. X LAW" strings.
    """
    results = {}
    for decision in decisions:
        decision_id = decision.get("decision_id", "")
        full_text = decision.get("full_text", "")
        
        if not full_text:
            results[decision_id] = []
            continue
        
        refs = extract_statutes_from_text(full_text, max_results=max_per_decision)
        statutes = [f"{r.article} {r.law_abbrev}" for r in refs]
        results[decision_id] = statutes
    
    return results


def enrich_decision_statutes(
    decisions: List[Dict[str, Any]],
    max_per_decision: int = 200
) -> List[Dict[str, Any]]:
    """
    Enrich canonical decisions with extracted statutes where cited_laws is empty.
    Returns list of decisions with cited_laws enriched.
    """
    for decision in decisions:
        existing_laws = decision.get("cited_laws") or []
        
        if not existing_laws:
            # Extract from full_text
            refs = extract_statutes_from_text(
                decision.get("full_text", ""),
                max_results=max_per_decision
            )
            if refs:
                decision["cited_laws"] = [f"{r.article} {r.law_abbrev}" for r in refs]
    
    return decisions


# Statistics about Swiss law abbreviations in BGer corpus
def get_law_abbreviation_stats(
    decisions: List[Dict[str, Any]],
    top_n: int = 20
) -> List[Dict[str, Any]]:
    """Get frequency statistics of law abbreviations in the corpus."""
    from collections import Counter
    
    law_counter = Counter()
    article_counter = Counter()
    
    for decision in decisions:
        refs = extract_statutes_from_text(decision.get("full_text", ""))
        for ref in refs:
            law_counter[ref.law_abbrev] += 1
            article_counter[f"{ref.article} {ref.law_abbrev}"] += 1
    
    return {
        "top_laws": [{"law": law, "count": count, "full_name": SWISS_LAW_ABBREVS.get(law, "Unknown")}
                     for law, count in law_counter.most_common(top_n)],
        "top_articles": [{"article": art, "count": count}
                        for art, count in article_counter.most_common(top_n)],
        "total_references": sum(law_counter.values()),
        "unique_laws": len(law_counter),
    }
