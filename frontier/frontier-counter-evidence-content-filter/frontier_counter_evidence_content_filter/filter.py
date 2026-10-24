from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any


LETTERHEAD_ZONE_OFFSET_MAX = 400


def _normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def _strip_markup(s: str) -> str:
    # Remove HTML/XML-like tags and common escape residues
    s2 = re.sub(r"<[^>]+>", " ", s or "")
    s2 = re.sub(r"&[a-zA-Z]+;", " ", s2)
    s2 = re.sub(r"&#\d+;", " ", s2)
    return s2


def _has_markup_residue(s: str) -> bool:
    if not s:
        return False
    if re.search(r"<[a-zA-Z/!]", s):
        return True
    if re.search(r"&[a-zA-Z]+;", s):
        return True
    if re.search(r"&#\d+;", s):
        return True
    # mark tags specifically as in evidence
    if "<mark" in s or "</mark>" in s:
        return True
    return False


# Court/header identifying patterns for letterhead zone
LETTERHEAD_PATTERNS = [
    r"Kantonsgericht",
    r"Dretgira\s+chantunala",
    r"Tribunale\s+cantonale",
    r"Bundesgericht",
    r"Tribunal\s+f[ée]d[ée]ral",
    r"Tribunale\s+federale",
    r"Court\s+of",
    r"Obergericht",
    r"Bezirksgericht",
    r"Amtsgericht",
    r"Landgericht",
    r"cour\s+d'appel",
    r"tribunal\s+cantonal",
]

# Pre-substantive header markers
HEADER_MARKERS = [
    r"^Kantonsgericht",
    r"^Bundesgericht",
    r"^Tribunal",
    r"^Dretgira",
    r"________________________",
    r"_____+",
]


def is_letterhead_zone(span_text: str, full_text: str | None = None, first_offset: int | None = None) -> bool:
    if not span_text:
        return False
    s = span_text
    # check offset if provided
    if first_offset is not None and first_offset <= LETTERHEAD_ZONE_OFFSET_MAX:
        # if in early zone and contains header patterns, likely letterhead
        pass
    # check patterns
    for pat in LETTERHEAD_PATTERNS:
        if re.search(pat, s, re.I):
            # also consider if it's at start of header block
            break
    else:
        # no court pattern found; also check if it's header markers
        for pat in HEADER_MARKERS:
            if re.search(pat, s, re.I | re.M):
                break
        else:
            return False
    # If in letterhead zone by offset
    if first_offset is not None and first_offset <= LETTERHEAD_ZONE_OFFSET_MAX:
        # Additional check: header-like structure
        if re.search(r"Kantonsgericht|Dretgira|Tribunale\s+cantonale|Tribunal\s+f[ée]d[ée]ral|Bundesgericht", s, re.I):
            return True
        if re.search(r"________________________|^Regeste|Consid[ée]rant", s, re.I | re.M) and first_offset < 50:
            return True
    # Also catch header block at very start
    if first_offset == 0:
        if re.search(r"Kantonsgericht|Dretgira|Tribunale\s+cantonale|Bundesgericht", s, re.I):
            return True
    return False


DEFAULT_LANGUAGE_MARKERS = {
    "de": ["Regeste", "Erwägung", "Kündigung", "Mietvertrag", "Bundesgericht", "Verfügung"],
    "fr": ["Considérant", "résiliation", "bail", "Tribunal fédéral", "recours", "art."],
    "it": ["Dispositivo", "risoluzione", "affitto", "Tribunale federale", "ricorso", "regola"],
}


def language_marker_mismatch(span_text: str, row_language: str, marker_sets: dict[str, list[str]] | None = None) -> bool:
    if not row_language:
        return False
    lang = str(row_language).strip().lower()
    if lang not in ("de", "fr", "it"):
        return False
    marker_sets = marker_sets or DEFAULT_LANGUAGE_MARKERS
    own = marker_sets.get(lang) or []
    others = []
    for l2, m2 in marker_sets.items():
        if l2 != lang:
            others.extend(m2)
    s = span_text or ""
    s_low = s.lower()
    own_hits = sum(1 for m in own if m.lower() in s_low)
    other_hits = sum(1 for m in others if m.lower() in s_low)
    # Match the probe logic: if row language has own markers but text has markers from others and few/no own markers in that context
    if own_hits == 0 and other_hits > 0:
        return True
    # Also catch case where clearly other language dominates
    if other_hits >= 2 and own_hits == 0:
        return True
    return False


@dataclass
class FilterResult:
    accepted: bool
    reject_reasons: list[str]
    defects_caught: list[str]
    details: dict[str, Any]


class CounterEvidenceContentFilter:
    def __init__(self, marker_sets: dict[str, list[str]] | None = None, letterhead_zone_max: int = LETTERHEAD_ZONE_OFFSET_MAX):
        self.marker_sets = marker_sets or DEFAULT_LANGUAGE_MARKERS
        self.letterhead_zone_max = letterhead_zone_max

    def filter_span(self, row: dict[str, Any]) -> FilterResult:
        span = row.get("counter_evidence") or row.get("evidence") or row.get("span") or ""
        if isinstance(span, list) and span:
            span = span[0] if isinstance(span[0], str) else str(span[0])
        span = str(span or "")
        full_text = str(row.get("full_text") or row.get("text") or "")
        language = str(row.get("language") or "")
        first_offset = row.get("first_offset")
        if first_offset is None and row.get("detail") and isinstance(row.get("detail"), dict):
            first_offset = row["detail"].get("first_offset") or row["detail"].get("offset")
        try:
            first_offset_int = int(first_offset) if first_offset is not None else None
        except Exception:
            first_offset_int = None

        reject_reasons = []
        defects_caught = []

        # D3: markup residue
        if _has_markup_residue(span):
            reject_reasons.append("D3_MARKUP_RESIDUE")
            defects_caught.append("D3_markup_residue")

        # D2: letterhead zone
        if is_letterhead_zone(span, full_text, first_offset_int):
            reject_reasons.append("D2_LETTERHEAD_ZONE")
            defects_caught.append("D2_letterhead_zone")
        # also if span is from header block at very start
        elif first_offset_int == 0 and re.search(r"Kantonsgericht|Dretgira|Tribunale\s+cantonale|Bundesgericht", span, re.I):
            reject_reasons.append("D2_LETTERHEAD_ZONE")
            defects_caught.append("D2_letterhead_zone")

        # D4: language marker mismatch
        if language_marker_mismatch(span, language, self.marker_sets):
            reject_reasons.append("D4_LANGUAGE_MARKER_MISMATCH")
            defects_caught.append("D4_language_marker_mismatch")

        if reject_reasons:
            return FilterResult(accepted=False, reject_reasons=reject_reasons, defects_caught=defects_caught, details={
                "first_offset": first_offset_int,
                "language": language,
                "span_head": span[:80],
            })
        return FilterResult(accepted=True, reject_reasons=[], defects_caught=[], details={
            "first_offset": first_offset_int,
            "language": language,
        })
