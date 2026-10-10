#!/usr/bin/env python3
"""Trilingual section segmentation for Swiss Federal Supreme Court decisions.

Extracts ``Sachverhalt`` (facts) / ``Erwaegungen`` (reasoning) / ``Dispositiv``
(operative part) from a decision's ``full_text`` for German, French and Italian.

Provenance / method
-------------------
The pattern tables and boundary logic are a faithful, trimmed adaptation of the
OpenCaseLaw structure extractor (project ``jonashertner/opencaselaw``,
``search_stack/extract_decision_structure.py``), which is the algorithm that
produced the independently published ``structure/structure.parquet`` in the
``voilaj/swiss-caselaw`` dataset (CC0-1.0). We vendor it so the corpus lane owns
a *reproducible*, *offline*, dependency-free segmentation that can be validated
against that independently published per-decision section-presence table.

Adaptations for the LexMachina corpus lane:
  * Returns character spans (``SectionSpan``) as well as text, so the extraction
    can be persisted compactly and materialised deterministically from the
    pinned parquet without storing ~2 GB of duplicated full text.
  * The BGE-historical (volumes 1-79) and ECtHR paths are omitted: the pinned
    bger corpus is 2000-onward and contains no such decisions.
  * No SQLite sidecar; the caller persists whatever representation it needs.

This module is intentionally self-contained: ``extract_structure`` has no
third-party dependencies.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Marker patterns — federal-court tuned (BGer/BVGer/BStGer/BGE)
# (OpenCaseLaw, CC0-1.0)
# ---------------------------------------------------------------------------
DISPOSITIV_PATTERNS = {
    "de": [
        (r"Demnach\s+erkennt\s+das\s+Bundesgericht\s*:?", "ranked_de_BGer"),
        (r"Demnach\s+erkennt\s+das\s+Bundesverwaltungsgericht\s*:?", "ranked_de_BVGer"),
        (r"Demnach\s+erkennt\s+das\s+Bundesstrafgericht\s*:?", "ranked_de_BStGer"),
        (r"Demnach\s+erkennt\s+(?:das|die)\s+(?:Bundesgericht|Bundesverwaltungsgericht|Bundesstrafgericht|Bundespatentgericht|Beschwerdekammer|Strafkammer|Anklagekammer|Berufungskammer|I+\.\s+Kammer|Abteilung)[^:\n]*:?", "ranked_de_court"),
        (r"Demnach\s+erkennt\s+(?:der|die)\s+(?:Präsident|Präsidentin|Instruktionsrichter|Einzelrichter|Vizepräsident)[^:\n]*:?", "ranked_de_judge"),
        (r"Demnach\s+(?:verfügt|beschliesst|verfügen|beschliessen)\s+(?:das|der|die)\s+[^:\n]*:?", "ranked_de_verfuegt"),
        (r"Demnach\s+wird\s+(?:erkannt|verfügt|beschlossen)\s*:?", "ranked_de_passive"),
        (r"Aus\s+diesen\s+(?:Gründen|Erwägungen)\s+(?:erkennt|beschliesst|verfügt|ergibt|ist|kann)\b", "fallback_de_aus_gruenden"),
        (r"Demgemäss\s+(?:erkennt|beschliesst|verfügt)\b", "fallback_de_demgemaess"),
    ],
    "fr": [
        (r"Par\s+ces\s+motifs,?\s+le\s+Tribunal\s+(?:fédéral|militaire\s+de\s+cassation|administratif\s+fédéral|pénal\s+fédéral)\s+(?:prononce|ordonne|arrête)\s*:?", "ranked_fr_TF"),
        (r"Par\s+ces\s+motifs,?\s+(?:la\s+Cour|le\s+Président|la\s+Présidente|le\s+Juge\s+instructeur|le\s+Vice-président)[^:\n]*(?:prononce|ordonne|arrête)\s*:?", "ranked_fr_judge"),
        (r"Par\s+ces\s+motifs,?\s+(?:la\s+Cour|le\s+Tribunal|le\s+Président|la\s+Présidente)\b", "fallback_fr_par_ces_motifs"),
        (r"Par\s+ces\s+motifs\s*:?\s*$", "fallback_fr_bare"),
        (r"par\s+ces\s+motifs,?\s+prononce\s*:?", "fallback_fr_lc_prononce"),
    ],
    "it": [
        (r"Per\s+questi\s+motivi,?\s+il\s+Tribunale\s+(?:federale|militare\s+di\s+cassazione|amministrativo\s+federale|penale\s+federale)\s+pronuncia\s*:?", "ranked_it_TF"),
        (r"Per\s+questi\s+motivi,?\s+(?:il\s+)?(?:Presidente|Giudice\s+istruttore|la\s+Corte(?:\s+dei\s+reclami\s+penali)?)[^:\n]*pronuncia\s*:?", "ranked_it_court"),
        (r"Per\s+questi\s+motivi,?\s+il\s+Tribunale\s+federale\b", "fallback_it_TF_loose"),
        (r"Per\s+questi\s+motivi\s*:?\s*$", "fallback_it_bare"),
        (r"\bdecreta\s*:", "ranked_it_decreta"),
    ],
}

ERWAEGUNGEN_PATTERNS = {
    "de": [
        (r"Das\s+Bundesgericht\s+zieht\s+in\s+Erwägung\s*:?", "ranked_de_zieht_BGer"),
        (r"Das\s+Bundesverwaltungsgericht\s+zieht\s+in\s+Erwägung\s*:?", "ranked_de_zieht_BVGer"),
        (r"Das\s+Bundesstrafgericht\s+zieht\s+in\s+Erwägung\s*:?", "ranked_de_zieht_BStGer"),
        (r"(?:Das|Die)\s+(?:Beschwerdekammer|Strafkammer|Berufungskammer|Anklagekammer|Abteilung)\s+zieht\s+in\s+Erwägung\s*:?", "ranked_de_zieht_chamber"),
        (r"^\s*Aus\s+den\s+Erwägungen\s*:?\s*$", "ranked_de_BGE_aus_den"),
        (r"(?:hat|haben)\s+(?:in\s+Erwägung\s+gezogen|erwogen)\s*:?", "ranked_de_erwaegung_gezogen"),
        (r"in\s+Erwägung,?\s+dass\b", "ranked_de_in_erwaegung"),
        (r"zieht\s+(?:der|die|das)\s+[^:\n]{0,100}?in\s*Erwägung\s*:?", "ranked_de_zieht_cantonal"),
        (r"in\s*Erwägung\s*:", "ranked_de_inerwaegung_colon"),
        (r"^\s*Erwägungen\s*:?\s*$", "ranked_de_header"),
        (r"^\s*Erwägung\s*:?\s*$", "ranked_de_singular"),
    ],
    "fr": [
        (r"Extrait\s+des\s+considérants\s*:?", "ranked_fr_BGE_extrait"),
        (r"C\s+O\s+N\s+S\s+I\s+D\s+E\s+R\s+A\s+N\s+T(?:\s+en\s+droit)?", "ranked_fr_ne_spaced"),
        (r"Le\s+Tribunal\s+(?:fédéral|administratif\s+fédéral|pénal\s+fédéral)\s+considère\s+en\s+(?:droit|fait)\s*:?", "ranked_fr_considere_TF"),
        (r"(?:La\s+Cour|le\s+Tribunal|la\s+Chambre)[^.\n]*considère\s+en\s+(?:droit|fait)\s*:?", "ranked_fr_considere_court"),
        (r"considère\s+en\s+(?:fait\s+et\s+en\s+)?(?:droit|fait)\s*:?", "ranked_fr_considere_loose"),
        (r"Considérant\s+en\s+(?:fait\s+et\s+en\s+)?(?:droit|fait)\s*:?", "ranked_fr_considerant_endroit"),
        (r"\bConsidérant\s+(?:en\s+(?:droit|fait)|que)\b", "ranked_fr_considerant"),
        (r"^\s*Considérant\s*:\s*$", "ranked_fr_bare_header"),
        (r"^\s*Considérants?\s*:?\s*$", "ranked_fr_header"),
        (r"^\s*EN\s+DROIT\s*:?\s*$", "ranked_fr_uppercase"),
    ],
    "it": [
        (r"Estratto\s+dei\s+considerandi\s*:?", "ranked_it_BGE_estratto"),
        (r"^\s*Dai\s+considerandi\s*:?\s*$", "ranked_it_BGE_dai"),
        (r"^\s*Considerandi\s*:?\s*$", "ranked_it_considerandi_header"),
        (r"Il\s+Tribunale\s+(?:federale|amministrativo\s+federale|penale\s+federale)\s+considera\s+in\s+(?:diritto|fatto)\s*:?", "ranked_it_considera_TF"),
        (r"(?:La\s+Corte(?:\s+dei\s+reclami\s+penali)?|Il\s+Tribunale|Il\s+Giudice)[^.\n]*considera\s+in\s+(?:diritto|fatto)\s*:?", "ranked_it_considera_court"),
        (r"considera\s+in\s+(?:fatto\s+ed?\s+in\s+)?(?:diritto|fatto)\s*:?", "ranked_it_considera_loose"),
        (r"considerato\s*,?\s*in\s*diritto\s*:?", "ranked_it_considerato_glued"),
        (r"\bConsiderando\s+(?:in\s+(?:diritto|fatto)|che)\b", "ranked_it_considerando"),
        (r"^\s*Considerando\s+in\s+diritto\s*:?\s*$", "ranked_it_header"),
        (r"^\s*Diritto\s*:\s*$", "ranked_it_diritto_header"),
        (r"^\s*IN\s+DIRITTO\s*:?\s*$", "ranked_it_uppercase"),
    ],
}

SACHVERHALT_PATTERNS = {
    "de": [
        (r"^\s*Sachverhalt\s*:?\s*$", "ranked_de_header"),
        (r"\bSachverhalt\s*:?\s*\n", "ranked_de_inline"),
        (r"^A\.\s*-\s*", "fallback_de_alphabetic"),
    ],
    "fr": [
        (r"^\s*Faits\s*:?\s*$", "ranked_fr_header"),
        (r"\bFaits\s*:?\s*\n", "ranked_fr_inline"),
        (r"^A\.\s*-\s*", "fallback_fr_alphabetic"),
    ],
    "it": [
        (r"^\s*Fatti\s*:?\s*$", "ranked_it_header"),
        (r"\bFatti\s*:?\s*\n", "ranked_it_inline"),
        (r"^A\.\s*-\s*", "fallback_it_alphabetic"),
    ],
}

DISPOSITIV_FALLBACK_RE = re.compile(
    r"(?:^|\n)\s*1\.\s+.{20,800}?(?:^|\n)\s*\d+\.\s+.{10,800}?(?:Lausanne|Bellinzona|Berne|Bern|"
    r"St\.\s*Gallen|Dieses\s+Urteil\s+wird|Le\s+présent\s+(?:arrêt|jugement)|"
    r"La\s+presente\s+(?:sentenza|decisione)|Mitteilung)",
    re.DOTALL | re.MULTILINE,
)

MKG_TRAILER_RE = re.compile(
    r"\(\s*(?:MKG|TMC|TMCa|ATMC|STMC|N(?:r\.?|°)|no\.?)?\s*"
    r"\d{2,4}(?:\.\d+)?(?:\s*(?:/|et|und)\s*\d{2,4}(?:\.\d+)?)*\s*"
    r"(?:,\s*(?:arr[eê]t\s+(?:du|rendu\s+le)\s+|urteil\s+vom\s+|sentenza\s+del\s+|del\s+)?"
    r"|\s+(?:du|del|vom)\s+)"
    r"\d{1,2}\.?\s*[A-Za-zÄÖÜäöüéèàùç]+\.?\s*\d{4}\s*,\s*[^()]{2,200}\)\s*$",
    re.I | re.MULTILINE,
)


@dataclass
class SectionSpan:
    text: str
    start: int
    end: int
    method: str


@dataclass
class DecisionStructure:
    decision_id: str = ""
    language: str = ""
    sachverhalt: Optional[SectionSpan] = None
    erwaegungen: Optional[SectionSpan] = None
    dispositiv: Optional[SectionSpan] = None
    dispositiv_orders: list = field(default_factory=list)


def _find(text, patterns, lang):
    for pat, label in patterns.get(lang, []):
        m = re.search(pat, text, flags=re.MULTILINE | re.IGNORECASE)
        if m:
            return m.start(), m.end(), label
    return None, None, None


def _split_dispositiv_orders(disp_text):
    items = []
    matches = list(re.finditer(r"(?:^|\n)\s*(\d+)\.\s+", disp_text))
    if not matches:
        return [disp_text.strip()] if disp_text.strip() else []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(disp_text)
        body = disp_text[start:end].strip()
        if i == len(matches) - 1:
            cut_re = re.search(
                r"\n\s*(Lausanne|Bellinzona|Berne|Bern|St\.\s*Gallen|"
                r"Im\s+Namen|Au\s+nom|In\s+nome|Dieses\s+Urteil\s+wird|"
                r"La\s+greffière|Le\s+greffier|Le\s+Président|Der\s+Präsident|Il\s+Presidente)",
                body,
            )
            if cut_re:
                body = body[: cut_re.start()].strip()
        if body:
            items.append(body)
    return items


def extract_structure(full_text: str, language: str = "de", decision_id: str = "") -> DecisionStructure:
    """Extract Sachverhalt / Erwaegungen / Dispositiv spans from one decision.

    This is a faithful adaptation of OpenCaseLaw's ``extract()`` but returns
    spans (start/end into ``full_text``) so the result is compactly storable.
    """
    out = DecisionStructure(decision_id=decision_id, language=language)
    text = full_text or ""
    if not text:
        return out
    lang = (language or "de").lower()
    if lang not in DISPOSITIV_PATTERNS:
        lang = "de"

    disp_start, disp_end, disp_method = _find(text, DISPOSITIV_PATTERNS, lang)
    if disp_start is not None:
        body = text[disp_end:].strip()
        body = MKG_TRAILER_RE.sub("", body).strip()
        out.dispositiv = SectionSpan(body, disp_end, len(text), disp_method)
        out.dispositiv_orders = _split_dispositiv_orders(body)
    else:
        m = DISPOSITIV_FALLBACK_RE.search(text)
        if m:
            disp_start = m.start()
            body = text[disp_start:].strip()
            body = MKG_TRAILER_RE.sub("", body).strip()
            out.dispositiv = SectionSpan(body, disp_start, len(text), "fallback_enum_near_end")
            out.dispositiv_orders = _split_dispositiv_orders(body)

    erw_start, erw_end, erw_method = _find(text, ERWAEGUNGEN_PATTERNS, lang)
    if erw_start is not None:
        end_idx = disp_start if disp_start is not None and disp_start > erw_end else len(text)
        raw = text[erw_end:end_idx]
        raw = MKG_TRAILER_RE.sub("", raw).strip()
        out.erwaegungen = SectionSpan(raw, erw_end, end_idx, erw_method)

    sav_start, sav_end, sav_method = _find(text, SACHVERHALT_PATTERNS, lang)
    if sav_start is not None:
        end_idx = erw_start if erw_start is not None and erw_start > sav_end else (
            disp_start if disp_start is not None and disp_start > sav_end else len(text)
        )
        out.sachverhalt = SectionSpan(text[sav_end:end_idx].strip(), sav_end, end_idx, sav_method)

    # Inferred Erwaegungen: Sachverhalt found but no explicit marker.
    if out.erwaegungen is None and sav_start is not None:
        inferred_end = disp_start if disp_start is not None and disp_start > sav_end else len(text)
        inferred_body = text[sav_end:inferred_end]
        inferred_body = MKG_TRAILER_RE.sub("", inferred_body).strip()
        if len(inferred_body) > 100:
            out.erwaegungen = SectionSpan(inferred_body, sav_end, inferred_end,
                                          "inferred_from_sachverhalt_dispositiv_bounds")

    # Numerical-headers fallback (cantonal-style decisions).
    if out.erwaegungen is None:
        candidates = _validate_erw_sequence(_erw_candidates(text))
        top_level = [c for c in candidates if "." not in c[2]]
        if len(top_level) >= 3:
            first_start = top_level[0][0]
            tail_end = disp_start if disp_start is not None and disp_start > first_start else len(text)
            body = text[first_start:tail_end]
            body = MKG_TRAILER_RE.sub("", body).strip()
            if len(body) > 100:
                out.erwaegungen = SectionSpan(body, first_start, tail_end, "fallback_numerical_headers")

    return out


# ---------------------------------------------------------------------------
# Erwaegungen paragraph parser (OpenCaseLaw, CC0-1.0)
# ---------------------------------------------------------------------------
ERW_PARA_RE = re.compile(
    r"(?m)^[ \t]*(\d+(?:\.\d+){0,3})\.?[ \t]*[\-\u2013\u2014]?[ \t]*(?:$|[\n\r])"
)
ERW_PARA_RE_INLINE = re.compile(
    r"(?m)^[ \t]*(\d+(?:\.\d+){0,3})\.?[ \t]*[\-\u2013\u2014]?[ \t]+(?=\S)"
)

_NOT_A_MARKER_AFTER = re.compile(
    r"(?:janvier|f[ée]vrier|mars|avril|mai|juin|juillet|ao[uû]t|septembre|octobre|novembre|d[ée]cembre|"
    r"Januar|Februar|März|April|Juni|Juli|August|September|Oktober|November|Dezember|"
    r"gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|dicembre|"
    r"et|und|e|ed|oder|ou|o)\b", re.IGNORECASE)


def _erw_candidates(text):
    seen = {}
    for pat in (ERW_PARA_RE, ERW_PARA_RE_INLINE):
        for m in pat.finditer(text):
            if pat is ERW_PARA_RE_INLINE and "." not in m.group(1) and _NOT_A_MARKER_AFTER.match(text[m.end():m.end() + 12]):
                continue
            seen.setdefault(m.start(), (m.end(), m.group(1)))
    return sorted([(s, e, n) for s, (e, n) in seen.items()])


def _validate_erw_run(markers):
    out = []
    seen_paths = set()
    last_top = 0
    for start, end, e_num in markers:
        depth = e_num.count(".") + 1
        first_n = int(e_num.split(".")[0])
        if depth == 1:
            if first_n > 50:
                continue
            if first_n < last_top:
                continue
            if first_n > last_top + 5 and last_top > 0:
                continue
            out.append((start, end, e_num))
            seen_paths.add(e_num)
            last_top = first_n
        else:
            parent = ".".join(e_num.split(".")[:-1])
            last_subnum = int(e_num.split(".")[-1])
            if last_subnum > 30:
                continue
            if parent not in seen_paths:
                if first_n > 50 or first_n < last_top or (last_top and first_n > last_top + 5):
                    continue
                if out and first_n == last_top and parent.count(".") == 0 and any(p.startswith(parent + ".") for p in seen_paths):
                    pass
                elif out and first_n == last_top:
                    continue
                parts = parent.split(".")
                for i in range(1, len(parts) + 1):
                    seen_paths.add(".".join(parts[:i]))
                last_top = first_n
            out.append((start, end, e_num))
            seen_paths.add(e_num)
    return out


def _validate_erw_sequence(markers):
    if not markers:
        return []
    starts = [0] + [i for i, (_, _, n) in enumerate(markers) if i and n.split(".")[0] == "1"]
    best = []
    for i in starts[:12]:
        run = _validate_erw_run(markers[i:])
        if len(run) > len(best):
            best = run
    return best


_LETTER_MARK_RE = re.compile(r"(?m)(?:^[ \t]*|(?<=\) ))([a-z]{1,2})\)[ \t]+(?=\S)")


def _lettered_units(parent_num, parent_depth, body):
    marks = [(m.start(), m.end(), m.group(1)) for m in _LETTER_MARK_RE.finditer(body)]
    if not marks:
        return []
    singles = [(s, e, l) for s, e, l in marks if len(l) == 1]
    doubles = [(s, e, l) for s, e, l in marks if len(l) == 2]
    units = []

    def ordered(run, letters):
        return bool(run) and [l for _, _, l in run][:len(letters)] == letters[:len(run)]

    alphabet = [chr(c) for c in range(ord("a"), ord("z") + 1)]
    if singles and ordered(singles, alphabet):
        for i, (s, e, letter) in enumerate(singles):
            nxt = singles[i + 1][0] if i + 1 < len(singles) else len(body)
            text = body[e:nxt].strip()
            if not text:
                continue
            number = f"{parent_num}{letter}"
            units.append({"e_number": number, "depth": parent_depth + 1, "parent": parent_num, "text": text})
            inner = [(ds - e, de - e, dl) for ds, de, dl in doubles if e <= ds < nxt]
            if inner and ordered(inner, [c * 2 for c in alphabet]):
                for j, (ds, de, dl) in enumerate(inner):
                    dn = inner[j + 1][0] if j + 1 < len(inner) else len(text)
                    sub = text[de:dn].strip()
                    if sub:
                        units.append({"e_number": f"{number}/{dl}", "depth": parent_depth + 2, "parent": number, "text": sub})
    elif doubles and ordered(doubles, [c * 2 for c in alphabet]):
        for j, (ds, de, dl) in enumerate(doubles):
            dn = doubles[j + 1][0] if j + 1 < len(doubles) else len(body)
            sub = body[de:dn].strip()
            if sub:
                units.append({"e_number": f"{parent_num}{dl}", "depth": parent_depth + 1, "parent": parent_num, "text": sub})
    return units


def parse_erwaegungen_paragraphs(erw_text):
    if not erw_text:
        return []
    candidates = _erw_candidates(erw_text)
    valid = _validate_erw_sequence(candidates)
    if not valid:
        return [{"e_number": "0", "depth": 0, "parent": None, "text": erw_text.strip()}]
    paragraphs = []
    for i, (m_start, m_end, e_num) in enumerate(valid):
        next_start = valid[i + 1][0] if i + 1 < len(valid) else len(erw_text)
        body = erw_text[m_end:next_start].strip()
        if not body:
            continue
        depth = e_num.count(".") + 1
        paragraphs.append({
            "e_number": e_num,
            "depth": depth,
            "parent": ".".join(e_num.split(".")[:-1]) if e_num.count(".") else None,
            "text": body,
        })
        paragraphs.extend(_lettered_units(e_num, depth, body))
    return paragraphs
