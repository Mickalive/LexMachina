"""
LexMachina Section Extractor
Extracts structured sections (Sachverhalt, Erwägungen, Dispositiv) from
Swiss Federal Supreme Court decision full_text.

Supports German, French, and Italian decision formats.
"""
import re
from typing import Optional, Dict, Tuple
from dataclasses import dataclass


@dataclass
class ExtractedSections:
    """Extracted section texts from a decision."""
    sachverhalt: Optional[str] = None
    erwaegungen: Optional[str] = None
    dispositiv: Optional[str] = None
    language: str = "de"
    extraction_method: str = "regex"


# Section markers by language
SECTION_MARKERS = {
    "de": {
        "sachverhalt": ["Sachverhalt:"],
        "erwaegungen": ["Erwägungen:"],
        "dispositiv": ["Demnach erkennt"],
    },
    "fr": {
        "sachverhalt": ["Faits:", "en fait:"],
        "erwaegungen": ["en droit:", "Considérant en fait et en droit"],
        "dispositiv": ["Par ces motifs"],
    },
    "it": {
        "sachverhalt": ["Fatti:"],
        "erwaegungen": ["considerando:", "in diritto:"],
        "dispositiv": ["per questi motivi"],
    },
}

# End markers (next section start or end of document)
END_MARKERS = {
    "de": ["Erwägungen:", "Demnach erkennt"],
    "fr": ["en droit:", "Par ces motifs"],
    "it": ["considerando:", "in diritto:", "per questi motivi"],
}


def _find_marker(text: str, markers: list, start: int = 0) -> Tuple[Optional[str], int]:
    """Find the earliest occurrence of any marker in the list."""
    earliest_pos = len(text)
    found_marker = None
    for marker in markers:
        pos = text.find(marker, start)
        if pos != -1 and pos < earliest_pos:
            earliest_pos = pos
            found_marker = marker
    if found_marker:
        return found_marker, earliest_pos
    return None, -1


def extract_sections(full_text: str, language: str = "de") -> ExtractedSections:
    """
    Extract Sachverhalt, Erwägungen, Dispositiv from decision full_text.
    
    Args:
        full_text: Complete decision text
        language: Language code (de, fr, it)
        
    Returns:
        ExtractedSections with extracted text (None if not found)
    """
    if not full_text:
        return ExtractedSections(language=language)
    
    lang = language.lower()
    if lang not in SECTION_MARKERS:
        lang = "de"  # fallback
    
    markers = SECTION_MARKERS[lang]
    result = ExtractedSections(language=language)
    
    # Find section start positions
    sachverhalt_marker, sachverhalt_pos = _find_marker(full_text, markers["sachverhalt"])
    erwaegungen_marker, erwaegungen_pos = _find_marker(full_text, markers["erwaegungen"])
    dispositiv_marker, dispositiv_pos = _find_marker(full_text, markers["dispositiv"])
    
    # Extract Sachverhalt: from its marker to next section or end
    if sachverhalt_pos >= 0:
        end_pos = len(full_text)
        # Find the next section marker after sachverhalt
        for next_marker_list in [markers["erwaegungen"], markers["dispositiv"]]:
            for next_marker in next_marker_list:
                pos = full_text.find(next_marker, sachverhalt_pos + len(sachverhalt_marker))
                if pos != -1 and pos < end_pos:
                    end_pos = pos
        # Extract text after the marker
        start = sachverhalt_pos + len(sachverhalt_marker)
        result.sachverhalt = full_text[start:end_pos].strip()
    
    # Extract Erwägungen: from its marker to next section or end
    if erwaegungen_pos >= 0:
        end_pos = len(full_text)
        for next_marker in markers["dispositiv"]:
            pos = full_text.find(next_marker, erwaegungen_pos + len(erwaegungen_marker))
            if pos != -1 and pos < end_pos:
                end_pos = pos
        start = erwaegungen_pos + len(erwaegungen_marker)
        extracted = full_text[start:end_pos].strip()
        # For French combined format, label as erwaegungen (contains both)
        result.erwaegungen = extracted
    
    # Extract Dispositiv: from its marker to end
    if dispositiv_pos >= 0:
        start = dispositiv_pos + len(dispositiv_marker)
        result.dispositiv = full_text[start:].strip()
    
    # Clean up: remove excessive whitespace
    for field in ["sachverhalt", "erwaegungen", "dispositiv"]:
        val = getattr(result, field)
        if val:
            # Collapse multiple newlines
            val = re.sub(r'\n{3,}', '\n\n', val)
            # Trim
            val = val.strip()
            setattr(result, field, val if val else None)
    
    return result


def extract_sections_from_record(record: Dict) -> Dict:
    """
    Extract sections from a decision record and return updated record.
    
    Adds/updates: sachverhalt, erwaegungen, dispositiv fields
    """
    full_text = record.get("full_text", "")
    language = record.get("language", "de")
    
    sections = extract_sections(full_text, language)
    
    # Only update if extraction found content
    if sections.sachverhalt:
        record["sachverhalt"] = sections.sachverhalt
    if sections.erwaegungen:
        record["erwaegungen"] = sections.erwaegungen
    if sections.dispositiv:
        record["dispositiv"] = sections.dispositiv
    
    return record


def has_extractable_sections(full_text: str, language: str = "de") -> bool:
    """Quick check if a decision has at least 2 extractable sections."""
    if not full_text:
        return False
    lang = language.lower()
    if lang not in SECTION_MARKERS:
        lang = "de"
    markers = SECTION_MARKERS[lang]
    found = 0
    for section_markers in markers.values():
        for m in section_markers:
            if m in full_text:
                found += 1
                break
    return found >= 2


def get_section_stats(corpus_dir: str) -> Dict:
    """Get statistics on section extractability across corpus."""
    import json
    from pathlib import Path
    
    stats = {"total": 0, "by_language": {}, "extractable": 0, "with_3_sections": 0}
    
    for jsonl_file in Path(corpus_dir).glob("*.jsonl"):
        with open(jsonl_file, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    stats["total"] += 1
                    lang = record.get("language", "de")
                    if lang not in stats["by_language"]:
                        stats["by_language"][lang] = {"total": 0, "extractable": 0, "with_3": 0}
                    stats["by_language"][lang]["total"] += 1
                    
                    full_text = record.get("full_text", "")
                    sections = extract_sections(full_text, lang)
                    n_sections = sum(1 for s in [sections.sachverhalt, sections.erwaegungen, sections.dispositiv] if s)
                    
                    if n_sections >= 2:
                        stats["extractable"] += 1
                        stats["by_language"][lang]["extractable"] += 1
                    if n_sections == 3:
                        stats["with_3_sections"] += 1
                        stats["by_language"][lang]["with_3"] += 1
                except json.JSONDecodeError:
                    continue
    
    return stats


if __name__ == "__main__":
    # Quick test
    test_text_de = """Bundesgericht
Sachverhalt:
A. Dies ist der Sachverhalt.
Erwägungen:
1. Dies sind die Erwägungen.
Demnach erkennt das Bundesgericht:
1. Dies ist der Dispositiv."""
    
    test_text_fr = """Tribunal fédéral
Faits:
A. Ceci est les faits.
en droit:
1. Ce sont les considérants.
Par ces motifs, le Tribunal fédéral prononce:
1. Ceci est le dispositif."""
    
    test_text_it = """Tribunale federale
Fatti:
A. Questi sono i fatti.
considerando:
1. Queste sono le considerazioni.
per questi motivi, il Tribunale federale pronuncia:
1. Questo è il dispositivo."""
    
    for lang, text in [("de", test_text_de), ("fr", test_text_fr), ("it", test_text_it)]:
        sections = extract_sections(text, lang)
        print(f"\n{lang.upper()}:")
        print(f"  Sachverhalt: {sections.sachverhalt[:50] if sections.sachverhalt else 'None'}...")
        print(f"  Erwägungen: {sections.erwaegungen[:50] if sections.erwaegungen else 'None'}...")
        print(f"  Dispositiv: {sections.dispositiv[:50] if sections.dispositiv else 'None'}...")
    
    # Test on real corpus
    print("\n=== Corpus Stats ===")
    stats = get_section_stats("results/corpus/normalization/canonical")
    print(f"Total: {stats['total']}")
    print(f"Extractable (>=2 sections): {stats['extractable']}")
    print(f"With 3 sections: {stats['with_3_sections']}")
    for lang, data in stats["by_language"].items():
        print(f"  {lang}: total={data['total']}, extractable={data['extractable']}, 3-sections={data['with_3']}")