"""The frozen support rubric: one deterministic verdict per issued counter label.

Every lexicon, criterion, precedence step and threshold is read from RULES.json.
The module holds no legal judgement of its own: it computes the criterion marks
(i) to (v) and then applies the FROZEN assignment precedence in the frozen
order, first match wins, producing exactly one primary defect class per row.

Three passes are always produced:
  * ``primary``                     -- the frozen rubric as committed;
  * ``lenient-domain-only``         -- pre-declared sensitivity: criterion (v)
                                       without the authored PIVOT test;
  * ``strict-no-product-vocabulary``-- pre-declared sensitivity: criterion (i)
                                       without the product's own marker words.
Only ``primary`` is decisive.  The variants exist so that no single
authored interpretation can silently decide the verdict.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .normalize import Normalizer
from .rules import FrozenRules

VARIANT_PRIMARY = "primary"
VARIANT_LENIENT = "lenient-domain-only"
VARIANT_STRICT = "strict-no-product-vocabulary"
ALL_VARIANTS = (VARIANT_PRIMARY, VARIANT_LENIENT, VARIANT_STRICT)

#: Frozen precedence steps keyed by their frozen ``class`` name, in frozen order.
_SUPPORTED = "SUPPORTED"


@dataclass(frozen=True)
class RubricContext:
    rules: FrozenRules
    normalizer: Normalizer
    anchor_profile: dict[str, Any]
    marker_variant: str
    lenient_domain: bool


def _lang_of(row: dict[str, Any], fallback: str = "de") -> str:
    lang = str(row.get("language") or "").lower()
    return lang if lang in ("de", "fr", "it") else fallback


def _hits(nz: Normalizer, tokens: list[str], rx_text: str,
          terms: list[str], *, anchor: bool) -> list[str]:
    out: list[str] = []
    for term in terms or ():
        hit = nz.match_anchor(tokens, term) if anchor else nz.match_marker(tokens, term)
        if hit is not None and hit not in out:
            out.append(hit)
    return sorted(out)


def _rx_hits(nz: Normalizer, rx_text: str, patterns: list[str]) -> list[str]:
    out: list[str] = []
    for pat in patterns or ():
        if nz.match_regex(rx_text, pat) is not None and pat not in out:
            out.append(pat)
    return sorted(out)


def score_row(row: dict[str, Any], ctx: RubricContext) -> dict[str, Any]:
    """Score one issued counter label against the frozen rubric."""
    nz = ctx.normalizer
    lex = ctx.rules.lexicons
    language = _lang_of(row)
    evidence = str(row.get("counter_evidence") or "")
    evidence_present = bool(row["field_presence"].get("counter_evidence"))
    title = str(row.get("title") or "")
    regeste = str(row.get("regeste") or "")
    row_text = str(row.get("row_text") or "")

    ev_rx = nz.regex_text(evidence)
    ev_tokens = nz.stems(evidence)
    ctx_tokens = nz.stems(" ".join(x for x in (evidence, title, regeste) if x))
    title_tokens = nz.stems(" ".join(x for x in (evidence, title) if x))

    markers = ctx.rules.marker_lexicon(language, ctx.marker_variant)
    markers_hit = _hits(nz, ev_tokens, ev_rx, markers, anchor=False)
    markers_row_hit = _hits(nz, nz.stems(row_text), nz.regex_text(row_text), markers, anchor=False)

    inversion_hit = _rx_hits(nz, ev_rx, lex["polarity_inversion"].get(language) or [])
    procedural_hit = _rx_hits(nz, ev_rx, lex["procedural_formula"].get(language) or [])
    outcome_hit = _hits(nz, ev_tokens, ev_rx, lex["procedural_outcome_words"].get(language) or [], anchor=False)
    pointer_hit = _rx_hits(nz, nz.regex_text(evidence).strip(), lex["fragment_pointer"])

    profile = ctx.anchor_profile
    domain_anchors = list(profile.get("domain") or [])
    pivot_anchors = list(profile.get("pivot") or [])
    expected_languages = list(profile.get("expected_languages") or [])
    foreign_areas = list(profile.get("foreign_legal_area_fields") or [])

    domain_ctx = _hits(nz, ctx_tokens, ev_rx, domain_anchors, anchor=True)
    domain_ev_title = _hits(nz, title_tokens, ev_rx, domain_anchors, anchor=True)
    pivot_ctx = _hits(nz, ctx_tokens, ev_rx, pivot_anchors, anchor=True)

    evidence_absent = not evidence.strip()
    lang_ok = (not expected_languages) or (language in expected_languages)
    area_ok = str(row.get("legal_area") or "") not in foreign_areas

    # -- criteria -------------------------------------------------------
    marks = {
        "i": {"criterion": "intent_marker_in_cited_evidence", "pass": bool(markers_hit), "matches": markers_hit},
        "ii": {"criterion": "no_polarity_inversion", "pass": not inversion_hit, "matches": inversion_hit},
        "iii": {
            "criterion": "not_procedural_boilerplate_only",
            "pass": (not procedural_hit) or bool(outcome_hit) or bool(markers_hit),
            "matches": sorted(set(procedural_hit) | set(outcome_hit)),
        },
        "iv": {"criterion": "topical_term_in_evidence_or_title", "pass": bool(domain_ev_title), "matches": domain_ev_title},
        "v": {
            "criterion": "not_demonstrably_outside_question_domain",
            "pass": (bool(pivot_ctx) if not ctx.lenient_domain else True) and lang_ok and area_ok,
            "matches": pivot_ctx,
            "language_ok": lang_ok,
            "legal_area_ok": area_ok,
            "pivot_test_applied": not ctx.lenient_domain,
        },
    }

    # -- frozen precedence ---------------------------------------------
    firings: dict[int, bool] = {
        1: evidence_absent,
        2: bool(pointer_hit),
        3: bool(procedural_hit) and not markers_hit,
        4: bool(inversion_hit),
        5: (not pivot_ctx) if not ctx.lenient_domain else False,
        6: not markers_hit,
        7: not domain_ev_title,
        8: all(marks[k]["pass"] for k in ("i", "ii", "iii", "iv", "v")),
    }
    firings[5] = firings[5] or (not lang_ok) or (not area_ok)
    if ctx.lenient_domain:
        firings[5] = (not lang_ok) or (not area_ok)

    ordered = sorted(ctx.rules.rubric["assignment_precedence"], key=lambda s: int(s["step"]))
    primary_class, reason_code, fired_step = None, None, None
    for step in ordered:
        n = int(step["step"])
        if firings.get(n):
            primary_class = step["class"]
            reason_code = step["reason_code"]
            fired_step = n
            break

    all_pass = all(marks[k]["pass"] for k in ("i", "ii", "iii", "iv", "v"))
    if primary_class is None:  # defensive: frozen list must be total
        primary_class = _SUPPORTED if all_pass else "UNBACKED"
        reason_code = "supported" if all_pass else "no_intent_marker"
        fired_step = 8

    # Defect signals: every failing condition, primary class or not, so the
    # per-class breakdown can be audited and re-derived under any precedence.
    signals: list[str] = []
    if evidence_absent:
        signals.append("evidence_absent")
    if pointer_hit:
        signals.append("pointer_only")
    if procedural_hit:
        signals.append("procedural_formula")
    if inversion_hit:
        signals.append("polarity_inverted")
    if not lang_ok:
        signals.append("language_outside_expected")
    if not area_ok:
        signals.append("legal_area_foreign")
    if not pivot_ctx and not ctx.lenient_domain:
        signals.append("pivot_absent")
    if not markers_hit:
        signals.append("no_intent_marker")
    if not domain_ev_title:
        signals.append("no_domain_anchor")
    if not evidence.strip() or not bool(markers_hit):
        signals.append("no_cited_marker_evidence")

    reported_markers = row.get("counter_markers")
    if reported_markers is None:
        reported_markers_field_present = bool(row["field_presence"].get("counter_markers"))
        reported_markers_list: list[str] = []
        reported_source = "counter_reason" if row.get("counter_reason") else "none"
    else:
        reported_markers_field_present = True
        reported_markers_list = list(reported_markers or [])
        reported_source = "counter_markers"

    norm_row_text = nz.regex_text(row_text)
    norm_evidence = nz.regex_text(evidence)
    verbatim = None
    if norm_evidence:
        verbatim = norm_evidence in norm_row_text

    return {
        "decision_id": row.get("decision_id"),
        "counter_status": row.get("counter_status"),
        "rank": row.get("rank"),
        "language": language,
        "court": row.get("court"),
        "title": title,
        "regeste": regeste,
        "counter_reason": row.get("counter_reason"),
        "counter_confidence": row.get("counter_confidence"),
        "counter_uncertainty": row.get("counter_uncertainty"),
        "counter_evidence_verified": row.get("counter_evidence_verified"),
        "counter_evidence_verified_field_present": bool(row["field_presence"].get("counter_evidence_verified")),
        "cited_evidence": evidence,
        "cited_evidence_field_present": evidence_present,
        "cited_evidence_empty": evidence_absent,
        "cited_evidence_segments": [s for s in (str(evidence).split(";") if evidence else []) if s.strip()],
        "evidence_verbatim_in_row_text": verbatim,
        "full_text_len": row.get("full_text_len"),
        "row_text_len": len(row_text),
        "markers_precision": {
            "reported_field_present": reported_markers_field_present,
            "reported_source": reported_source,
            "markers_reported": sorted(reported_markers_list),
            "markers_reported_as_reason": row.get("counter_reason"),
            "markers_in_cited_evidence": markers_hit,
            "markers_in_row_text_document_wide": markers_row_hit,
            "document_wide_only_markers": sorted(set(markers_row_hit) - set(markers_hit)),
            "n_reported": len(reported_markers_list),
            "n_in_cited_evidence": len(markers_hit),
            "n_document_wide": len(markers_row_hit),
        },
        "criterion_marks": marks,
        "defect_signals": sorted(set(signals)),
        "primary_defect_class": primary_class,
        "reason_code": reason_code,
        "precedence_step_fired": fired_step,
        "supported": primary_class == _SUPPORTED,
        "all_criteria_pass": all_pass,
    }


def make_context(rules: FrozenRules, anchor_profile_key: str, variant: str) -> RubricContext:
    return RubricContext(
        rules=rules,
        normalizer=rules.normalizer,
        anchor_profile=rules.anchor_profile(anchor_profile_key),
        marker_variant=variant,
        lenient_domain=variant == VARIANT_LENIENT,
    )