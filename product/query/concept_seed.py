"""Product integration of the accepted NLCS-1 concept-seeded retrieval arm.

Why this exists
---------------
Factory direction v58, product lane ordered work (b): the accepted Frontier
team ``frontier-concept-seed-recall`` (team run 39237146851, independent audit
``results/audit/frontier/frontier-concept-seed-recall/CYCLE_39251875368_GATE.json``
gate=PASS / safe_to_integrate=true / required_fixes=[]) offers an additive,
free, deterministic retrieval arm behind the bundle seam.  Its integration
contract (``results/frontier/frontier-concept-seed-recall/integration_contract_39237146851.json``)
names ``product/query/pipeline.py`` as the seam and requires Product to record
an ADOPT/DECLINE decision under factory-wide requirement 21; silent
non-consumption is not permitted.

This module is that integration.  It is deliberately narrow:

* :func:`detect_question_language` - conservative de/fr/it detection.  A variant
  is emitted only when one language wins by a clear margin, so the product
  never invents a paraphrase for a language the question is not written in
  (the accepted module's own refusal).
* :func:`plan_concept_seed` - pure and offline: measure which of the question's
  own content concepts the retrieved set under-covers, then build one frozen
  NLCS-1 variant per under-covered concept (capped at 2, the accepted cap).
* :func:`augment_candidates` - strictly additive: one extra OpenCaseLaw search
  per planned variant, merged into the candidate pool with the
  ``concept_seed.nlcs`` channel.  Existing candidates are never removed,
  re-ranked or re-labelled.
* :func:`apply_concept_seed` - strictly additive provenance: appends the variant
  strings to ``bundle["query_variants"]`` and records the channel.  No decision
  is dropped, duplicated or re-labelled.

What this does NOT do
---------------------
It issues no model call, reads no corpus, mines no post-hoc vocabulary, invents
no synonym/translation/paraphrase, and does not classify any decision as
supporting/contrary/limiting.  The accepted arm's own claim ceiling is carried
verbatim in every provenance record it writes.

The adapter is reused, not modified: the extra search is issued through the
accepted ``ocl_adapter`` client/transport (so the content-addressed cache and
request-key derivation are the adapter's own), and the accepted ``nlcs.py`` is
vendored as ``product/query/nlcs.py``.  ``frontier/**`` is never edited.
"""
from __future__ import annotations

import re
from typing import Any, Callable, Iterable, Sequence

from . import nlcs
from .concept_coverage import coverage_report

#: The accepted arm's frozen cap (RULES.variant_construction.max_concepts_per_unit).
MAX_CONCEPTS_PER_QUERY = 2

#: Additive retrieval channel for rows that arrived through this arm.
CHANNEL = "concept_seed.nlcs"

#: Where the accepted component lives, for provenance.
COMPONENT = "frontier-concept-seed-recall/nlcs.py#NLCS-1"
ACCEPTED_RUN_ID = "39237146851"
ACCEPTED_AUDIT = (
    "results/audit/frontier/frontier-concept-seed-recall/CYCLE_39251875368_GATE.json"
)

#: The claim ceiling, carried verbatim from the accepted integration contract.
CLAIM_CEILING = (
    "No artifact may assert that a map helps a jurist, that any authority is "
    "absent from the corpus, that any frozen bar is met or moved, or that any "
    "packet is fit to serve. Usefulness remains the human product gate's "
    "question and admission remains fail-closed. Concept-coverage counts are "
    "lexical coverage of a retrieved set, not a legal conclusion; a zero count "
    "is a retrieval signal, not proof of corpus absence."
)

_TOKEN_RE = re.compile(r"[^\W\d_]+", re.UNICODE)

#: Conservative per-language token evidence.  A variant is emitted only when
#: one language wins by a clear margin, so the product never invents a
#: paraphrase for a language the question is not written in.
_LANGUAGE_MARKERS = {
    "de": (
        "der", "die", "das", "und", "bei", "mit", "nicht", "eine", "einer",
        "sich", "auch", "werden", "wird", "über", "gegenüber", "welche",
    ),
    "fr": (
        "le", "la", "les", "une", "des", "et", "est", "dans", "pour", "sur",
        "avec", "qui", "que", "par", "plus", "entre", "quelles", "ressortent",
    ),
    "it": (
        "il", "la", "le", "una", "del", "della", "dei", "degli", "che", "per",
        "con", "sono", "questa", "quale", "dalla", "dallo", "quali",
    ),
}


def detect_question_language(query_text: str) -> str | None:
    """Best-effort de/fr/it detection, or ``None`` when not confident.

    The accepted module refuses to emit a variant for a language whose question
    text is not an accepted text in that language.  The product's live query is
    not pre-registered, so the conservative rule is: require at least one marker
    token AND a strict win over the runner-up.  An ambiguous or marker-free
    query yields ``None`` and therefore no variant - never an invented language.
    """
    tokens = [t.lower() for t in _TOKEN_RE.findall(query_text or "")]
    if not tokens:
        return None
    scores = {
        lang: sum(1 for t in tokens if t in markers)
        for lang, markers in _LANGUAGE_MARKERS.items()
    }
    ordered = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    best_lang, best = ordered[0]
    if best == 0:
        return None
    runner_up = ordered[1][1]
    if best <= runner_up:
        return None
    return best_lang


def plan_concept_seed(
    query_text: str,
    decisions: Iterable[dict],
    *,
    language: str | None = None,
    max_concepts: int = MAX_CONCEPTS_PER_QUERY,
) -> dict:
    """Pure, offline plan: which frozen NLCS-1 variants should be issued.

    ``decisions`` is the already-retrieved candidate pool (dicts with the
    product's row fields).  The under-covered set is the product's own
    ``concept_coverage.coverage_report`` output, never a post-hoc vocabulary.
    """
    rows = [d for d in (decisions or []) if isinstance(d, dict)]
    report = coverage_report(query_text, rows)
    under = list(report.get("under_covered") or [])
    lang = language or detect_question_language(query_text)
    variants: list[dict] = []
    if lang and under:
        variants = nlcs.build_unit_variants(query_text, lang, under, max_concepts)
    return {
        "channel": CHANNEL,
        "component": COMPONENT,
        "enabled": bool(variants),
        "language": lang,
        "under_covered": under,
        "variants": variants,
        "model_calls": 0,
        "network_calls": 0,
        "note": (
            "one frozen NLCS-1 full-sentence variant per under-covered concept, "
            "capped at the accepted 2; emitted only for the question's own language"
        ),
    }


def augment_candidates(
    candidate_bundle: dict,
    plan: dict,
    *,
    search_fn: Callable[[str], Sequence[dict]] | None,
) -> dict:
    """Issue one additive search per planned variant and merge new candidates.

    ``search_fn(query_text)`` returns normalized candidate rows (the product
    supplies the accepted ``ocl_adapter`` client, so the content-addressed cache
    and request-key derivation are the adapter's own).  The merge is strictly
    additive: existing candidates are never removed, re-ranked or re-labelled;
    each new row gains the ``concept_seed.nlcs`` channel and a provenance entry.
    A ``search_fn`` that is absent or raises leaves the baseline untouched.
    """
    if not plan.get("enabled") or search_fn is None:
        return candidate_bundle
    variants = list(plan.get("variants") or [])
    existing = list(candidate_bundle.get("candidates") or [])
    seen = {str(c.get("decision_id")) for c in existing}
    added: list[dict] = []
    for variant in variants:
        try:
            rows = search_fn(variant["query"]) or []
        except Exception:  # retrieval must never abort the baseline
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            decision_id = str(row.get("decision_id") or "")
            if not decision_id or decision_id in seen:
                continue
            seen.add(decision_id)
            row = dict(row)
            channels = list(row.get("channels") or [])
            if CHANNEL not in channels:
                channels.append(CHANNEL)
            row["channels"] = channels
            added.append(row)
    if not added:
        return candidate_bundle
    out = dict(candidate_bundle)
    out["candidates"] = existing + added
    prov = dict(out.get("provenance") or {})
    prov["concept_seed"] = {
        "channel": CHANNEL,
        "component": COMPONENT,
        "accepted_run_id": ACCEPTED_RUN_ID,
        "accepted_audit": ACCEPTED_AUDIT,
        "enabled": True,
        "language": plan.get("language"),
        "under_covered": list(plan.get("under_covered") or []),
        "variants": [
            {
                "concept": v.get("concept"),
                "surface_form": v.get("surface_form"),
                "morph_variants": list(v.get("morph_variants") or []),
                "template_id": v.get("template_id"),
                "query": v.get("query"),
            }
            for v in variants
        ],
        "n_added_candidates": len(added),
        "added_decision_ids": [str(r.get("decision_id")) for r in added],
        "model_calls": 0,
        "network_calls": len(variants),
        "claim_ceiling": CLAIM_CEILING,
    }
    out["provenance"] = prov
    return out


def apply_concept_seed(bundle: dict, plan: dict) -> dict:
    """Strictly additive provenance on a product bundle (no re-rank, no label).

    Appends each planned variant to ``bundle["query_variants"]`` with
    ``kind="nl_concept_seeded"`` and records the channel under
    ``bundle["provenance"]["concept_seed"]``.  A decision that arrived through
    the channel keeps its existing provenance and gains the channel entry; the
    baseline rows are untouched.
    """
    if not plan.get("enabled"):
        return bundle
    variants = list(plan.get("variants") or [])
    query_variants = list(bundle.get("query_variants") or [])
    for variant in variants:
        query_variants.append(
            {
                "variant_id": (
                    f"nl_concept_seeded:{plan.get('language')}:{variant.get('concept')}"
                ),
                "text": variant.get("query"),
                "kind": "nl_concept_seeded",
                "language_filter": None,
                "terms_added": [],
                "terms_added_from": COMPONENT,
                "note": (
                    "accepted NLCS-1 natural-language concept-seeded variant for "
                    f"under-covered concept {variant.get('concept')!r}; additive, "
                    "no re-rank, no label"
                ),
            }
        )
    bundle["query_variants"] = query_variants
    prov = dict(bundle.get("provenance") or {})
    prov["concept_seed"] = {
        "channel": CHANNEL,
        "component": COMPONENT,
        "accepted_run_id": ACCEPTED_RUN_ID,
        "accepted_audit": ACCEPTED_AUDIT,
        "enabled": True,
        "language": plan.get("language"),
        "under_covered": list(plan.get("under_covered") or []),
        "variants": [
            {
                "concept": v.get("concept"),
                "surface_form": v.get("surface_form"),
                "morph_variants": list(v.get("morph_variants") or []),
                "template_id": v.get("template_id"),
                "query": v.get("query"),
            }
            for v in variants
        ],
        "model_calls": 0,
        "network_calls": "inherited from the adapter; this layer issues none",
        "claim_ceiling": CLAIM_CEILING,
    }
    bundle["provenance"] = prov
    return bundle


__all__ = [
    "CHANNEL",
    "CLAIM_CEILING",
    "COMPONENT",
    "MAX_CONCEPTS_PER_QUERY",
    "ACCEPTED_RUN_ID",
    "ACCEPTED_AUDIT",
    "apply_concept_seed",
    "augment_candidates",
    "detect_question_language",
    "plan_concept_seed",
]
