"""Executable gates for the frozen reality benchmark (evaluation lane).

Every gate returns a dict ``{"gate", "passed", "detail", "measured"}`` so a
verdict can always be recomputed from the artifact alone.  Gates that an
artifact cannot support are reported ``not_measurable`` with the reason;
they are never silently treated as passes.

Pure standard library; reuses the lane's bundle harness
(``evaluation/query_map/harness.py``) for the single-bundle structural checks.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Any
from urllib.parse import urlparse

from evaluation.query_map.harness import COUNTER_STATUSES
from evaluation.reality_gate import gate_contract

# Thresholds that decide pass/fail but are NOT carried by frozen_benchmark.json
# now come from the digest-pinned GATE_CONTRACT.json instead of being literals
# here, so editing them in this file does nothing and editing them anywhere
# trips the pin. See evaluation/reality_gate/gate_contract.py.
_CONTRACT = gate_contract.cached()
_ANSWER = _CONTRACT["answer"]
_SOURCE = _CONTRACT["source"]
_CORRUPTION = _CONTRACT["corruption"]
_MULTILINGUAL = _CONTRACT["multilingual"]
#: the only pass rule recall uses: >= this many hits of the frozen set (>=1-of-set)
MIN_RECALL_HITS = int(_CONTRACT["recall"]["min_hits_of_frozen_set"])

# --------------------------------------------------------------------------- #
# normalization (parity with the product's frozen reality gates)
# --------------------------------------------------------------------------- #


def normalize_text(value: object) -> str:
    import unicodedata
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.casefold().split())


# --------------------------------------------------------------------------- #
# language + corruption
# --------------------------------------------------------------------------- #

_STOPWORDS: dict[str, tuple[str, ...]] = {
    "fr": ("le", "la", "les", "un", "une", "des", "du", "de", "est", "dans",
           "pour", "par", "sur", "avec", "que", "qui", "son", "sa", "ses",
           "au", "aux", "pas", "plus", "entre", "sans", "chez", "ou"),
    "de": ("der", "die", "das", "und", "den", "dem", "des", "ist", "fuer",
           "von", "mit", "zu", "im", "sich", "eine", "ein", "auf", "nicht",
           "auch", "als", "bei", "nach", "ueber", "unter", "einem", "einer"),
    "it": ("il", "lo", "la", "i", "gli", "le", "un", "una", "di", "del",
           "della", "dei", "delle", "e", "per", "con", "che", "non", "sono",
           "piu", "tra", "fra", "nel", "nella", "allo", "alla"),
    "en": ("the", "a", "an", "of", "to", "in", "and", "is", "are", "for",
           "with", "that", "this", "be", "by", "as", "at", "from", "or"),
}


def classify_language(prose: str) -> dict:
    """Stopword-based dominant-language classification over normalized prose."""
    words = re.findall(r"[a-zà-ÿ']+", normalize_text(prose))
    counts = {}
    for lang, stops in _STOPWORDS.items():
        stops_set = set(stops)
        counts[lang] = sum(1 for w in words if w in stops_set)
    dominant = max(counts, key=lambda k: counts[k]) if any(counts.values()) else None
    return {"counts": counts, "dominant": dominant, "n_words": len(words)}


def detect_corruption(prose: str) -> list[str]:
    """Detect degenerate model output. Returns a list of corruption reasons.

    Deliberately conservative: only clear degeneration is flagged (repetition
    loops, mojibake), never style.
    """
    reasons: list[str] = []
    text = str(prose or "")
    norm = normalize_text(text)
    words = norm.split()
    n = len(words)

    ngram = int(_CORRUPTION["repetition_ngram"])
    # repetition loop: one n-gram covering more than
    # ``repetition_max_share`` of all n-grams (min ``repetition_min_words``)
    if n >= int(_CORRUPTION["repetition_min_words"]):
        grams = [tuple(words[i:i + ngram]) for i in range(n - ngram + 1)]
        if grams:
            top = Counter(grams).most_common(1)[0]
            if top[1] / len(grams) > float(_CORRUPTION["repetition_max_share"]):
                reasons.append(
                    f"repetition loop: {ngram}-gram {top[0][:4]}... covers "
                    f"{top[1]}/{len(grams)} of all {ngram}-grams"
                )
    # repeated sentence: a sentence repeated at least
    # ``repeated_sentence_min_repeats`` times (min ``repeated_sentence_min_sentences``)
    sentences = [s.strip() for s in re.split(r"[.!?]+\s+", norm)
                 if len(s.strip()) >= int(_CORRUPTION["repeated_sentence_min_chars"])]
    if len(sentences) >= int(_CORRUPTION["repeated_sentence_min_sentences"]):
        top_sentence = Counter(sentences).most_common(1)[0]
        if top_sentence[1] >= int(_CORRUPTION["repeated_sentence_min_repeats"]):
            reasons.append(
                f"repeated sentence x{top_sentence[1]}: {top_sentence[0][:60]!r}"
            )
    # mojibake / replacement chars
    if "�" in text:
        reasons.append("U+FFFD replacement characters present")
    if re.search(r"[À-ÿ]{2,}", text) and re.search(r"[ÃÂ][\x80-ÿ]", text):
        reasons.append("utf-8-decoded-as-latin1 mojibake pattern")
    control = sum(1 for ch in text if ord(ch) < 32 and ch not in "\n\t")
    if (len(text) > int(_CORRUPTION["control_char_min_chars"])
            and control / len(text) > float(_CORRUPTION["control_char_max_ratio"])):
        reasons.append(f"control-character ratio {control}/{len(text)}")
    return reasons


# --------------------------------------------------------------------------- #
# single-bundle structural checks (reuse the lane harness's semantics)
# --------------------------------------------------------------------------- #


def bundle_structural(bundle: dict) -> dict:
    """Structural checks computable from one final bundle (no initial needed)."""
    ids = [str(d.get("decision_id") or "") for d in bundle.get("decisions", [])]
    id_set = set(ids)
    cited = {str(x) for x in (bundle.get("answer") or {}).get("cited_decision_ids", [])}
    bad_sources = []
    for d in bundle.get("decisions", []):
        u = str(d.get("canonical_url") or "")
        p = urlparse(u)
        if (p.scheme != _SOURCE["required_scheme"]
                or p.hostname != _SOURCE["allowed_host"]):
            bad_sources.append(str(d.get("decision_id") or ""))
    unsupported_counters = []
    for d in bundle.get("decisions", []):
        if d.get("counter_status") not in COUNTER_STATUSES:
            continue
        evidence = str(d.get("counter_evidence") or "").strip()
        if not evidence or d.get("counter_uncertainty") is None:
            unsupported_counters.append(str(d.get("decision_id") or ""))
    return {
        "bundle_nonempty": bool(ids),
        "duplicate_free": len(ids) - len(id_set) == 0,
        "source_urls_valid": not bad_sources,
        "answer_citations_constrained": cited <= id_set,
        "counter_classifications_supported": not unsupported_counters,
        "bad_source_ids": bad_sources,
        "invalid_cited_ids": sorted(cited - id_set),
        "unsupported_counter_ids": unsupported_counters,
    }


# --------------------------------------------------------------------------- #
# gate evaluation
# --------------------------------------------------------------------------- #


def _out(gate: str, passed: bool, detail: str = "", **measured) -> dict:
    return {"gate": gate, "passed": bool(passed), "detail": detail, "measured": measured}


def _not_measurable(gate: str, reason: str) -> dict:
    return {"gate": gate, "passed": None, "detail": f"not_measurable: {reason}",
            "measured": {}}


def evaluate_truth_gates(question: dict, prose: str) -> list[dict]:
    norm = normalize_text(prose)
    out = []
    for gate in question["truth_gates"]:
        if gate["kind"] == "phrase":
            hit = next((p for p in gate["contains_any"] if p in norm), None)
            out.append(_out(
                f"truth::{gate['id']}",
                hit is not None,
                "" if hit else gate["detail"],
                matched_phrase=hit,
            ))
        elif gate["kind"] == "phrase_absent":
            bad = next((p for p in gate["absent_any"] if p in norm), None)
            out.append(_out(
                f"truth::{gate['id']}",
                bad is None,
                gate["detail"] if bad else "",
                matched_absent_phrase=bad,
            ))
        else:  # pragma: no cover - frozen spec is validated at load
            out.append(_out(f"truth::{gate['id']}", False, f"unknown gate kind {gate['kind']}"))
    return out


def evaluate_language_gate(question: dict, prose: str, spec: dict) -> dict:
    accepted = {question["language"]} | set(spec["accepted_answer_languages"]["fallback_languages"])
    info = classify_language(prose)
    dominant = info["dominant"]
    if dominant is None:
        return _out("language::dominant_in_accepted", False,
                    f"answer language undetectable (stopword counts {info['counts']})",
                    **info)
    counts = info["counts"]
    # a tie between two accepted languages (mixed FR/DE Swiss prose) is admissible
    tied = {k for k, v in counts.items() if v == counts[dominant]}
    ok = dominant in accepted or bool(tied & accepted)
    return _out(
        "language::dominant_in_accepted", ok,
        "" if ok else f"wrong-language answer: dominant={dominant}, accepted={sorted(accepted)}",
        **info,
    )


def evaluate_corruption_gate(prose: str) -> dict:
    reasons = detect_corruption(prose)
    return _out(
        "corruption::clean", not reasons,
        "; ".join(reasons),
        corruption_reasons=reasons,
    )


def evaluate_latency(total_seconds: float | None, budget: float) -> dict:
    if total_seconds is None:
        return _not_measurable("latency::under_budget", "artifact carries no full-run wall time")
    return _out(
        "latency::under_budget",
        total_seconds < budget,
        "" if total_seconds < budget
        else f"full run {total_seconds}s >= {budget}s budget",
        total_seconds=total_seconds, budget_seconds=budget,
    )


def evaluate_required_hits(required: list[str], found: set[str], kind: str,
                           available: bool) -> dict:
    """kind is 'citation' (answer cites) or 'retrieval' (bundle retrieved).

    At least one of the frozen controlling authorities must appear; the
    missing list is always reported so a regression names the exact authority.
    """
    if not required:
        return _out(f"recall::{kind}_controlling_authority", True,
                    "", required=[], found=0,
                    note="no frozen controlling set for this question")
    if not available:
        return _not_measurable(f"recall::{kind}_controlling_authority",
                               "artifact does not carry the full decision id list")
    hits = sorted(set(required) & found)
    missing = sorted(set(required) - found)
    return _out(
        f"recall::{kind}_controlling_authority",
        len(hits) >= MIN_RECALL_HITS,
        "" if len(hits) >= MIN_RECALL_HITS
        else f"missing {kind} of frozen controlling authority: {missing}",
        required=required, hits=hits, missing=missing,
    )


def evaluate_structural_from_report(report: dict) -> list[dict]:
    """Structural signals a slim reality-check leg report can carry.

    Slim reports are flat: ``answer_status`` / ``answer_method`` /
    ``answer_prose`` / ``provider_error`` / ``adversarial_*`` are top-level
    fields (see the producer's ``strip_bundle`` output shape).

    Detail is blank whenever a gate passes: a passing gate must not carry
    failure-flavoured prose into the record (record-readability rule).
    """
    errors = report.get("validation_errors") or []
    prose = str(report.get("answer_prose") or "")
    cited = report.get("cited_decision_ids") or []
    expected_answer = _ANSWER["expected_answer_method"]
    expected_adversarial = _ANSWER["expected_adversarial_method"]
    min_chars = int(_ANSWER["min_prose_chars"])
    out = [
        _out("structural::bundle_validation_clean", not errors,
             "" if not errors else f"bundle validation errors: {errors}",
             validation_errors=errors[:4]),
        _out("structural::answer_ready", report.get("answer_status") == "ready",
             "" if report.get("answer_status") == "ready"
             else f"answer status {report.get('answer_status')!r} != ready"),
        _out("structural::answer_method",
             report.get("answer_method") == expected_answer,
             "" if report.get("answer_method") == expected_answer
             else f"unexpected answer method: {report.get('answer_method')}"),
        _out("structural::prose_min_length", len(prose) >= min_chars,
             "" if len(prose) >= min_chars else "answer prose too short"),
        _out("structural::citations_nonempty", bool(cited),
             "" if cited else "answer cites nothing"),
        _out("structural::provider_clean",
             report.get("provider_error") in (None, ""),
             "" if report.get("provider_error") in (None, "")
             else f"provider error: {report.get('provider_error')}"),
        _out("structural::adversarial_method",
             report.get("adversarial_method") == expected_adversarial,
             "" if report.get("adversarial_method") == expected_adversarial
             else f"adversarial method: {report.get('adversarial_method')}"),
        _out("structural::adversarial_clean",
             report.get("adversarial_error") in (None, ""),
             "" if report.get("adversarial_error") in (None, "")
             else f"adversarial error: {report.get('adversarial_error')}"),
    ]
    return out


def evaluate_structural_from_bundle(bundle: dict) -> list[dict]:
    checks = bundle_structural(bundle)
    out = [
        _out("structural::bundle_nonempty", checks["bundle_nonempty"],
             "" if checks["bundle_nonempty"] else "bundle has no decisions"),
        _out("structural::duplicate_free", checks["duplicate_free"],
             "" if checks["duplicate_free"] else "duplicate decision ids in bundle"),
        _out("structural::source_urls_valid", checks["source_urls_valid"],
             "" if checks["source_urls_valid"]
             else f"non-OpenCaseLaw source urls: {checks['bad_source_ids'][:4]}"),
        _out("structural::answer_citations_constrained",
             checks["answer_citations_constrained"],
             "" if checks["answer_citations_constrained"]
             else f"answer cites ids outside the bundle: {checks['invalid_cited_ids'][:4]}"),
        _out("structural::counter_classifications_supported",
             checks["counter_classifications_supported"],
             "" if checks["counter_classifications_supported"]
             else f"counter rows without evidence/uncertainty: {checks['unsupported_counter_ids'][:4]}"),
        _not_measurable("structural::geometry_preserved",
                          "needs initial+final pair; single recorded bundle"),
        _not_measurable("structural::progressive_phases",
                          "needs initial+final pair; single recorded bundle"),
    ]
    return out


# --------------------------------------------------------------------------- #
# question-INDEPENDENT checks: run on EVERY recorded artifact of the relevant
# kind regardless of frozen-question match (audit repair R2).  Only gates whose
# inputs are the artifact alone are eligible: bundle structure, answer-prose
# corruption and recorded wall-time do not need the frozen question.  Truth /
# language / recall gates stay question-dependent and are reported
# ``not_measurable`` for unmatched artifacts, never silently passed.
# --------------------------------------------------------------------------- #


_BUNDLE_STRUCTURAL_GATES = (
    "structural::bundle_nonempty",
    "structural::duplicate_free",
    "structural::source_urls_valid",
    "structural::answer_citations_constrained",
    "structural::counter_classifications_supported",
)

_SLIM_STRUCTURAL_GATES = (
    "structural::bundle_validation_clean",
    "structural::answer_ready",
    "structural::answer_method",
    "structural::prose_min_length",
    "structural::citations_nonempty",
    "structural::provider_clean",
    "structural::adversarial_method",
    "structural::adversarial_clean",
)


def evaluate_question_independent_bundle(bundle: dict, spec: dict) -> list[dict]:
    """The bundle-structural subset that needs no frozen question match.

    Corruption and latency are measured whenever the artifact carries prose /
    timing; otherwise they are reported not_measurable with the reason.
    geometry/progressive stay not_measurable by construction (single bundle).
    """
    out = [g for g in evaluate_structural_from_bundle(bundle)
           if g["gate"] in _BUNDLE_STRUCTURAL_GATES]
    answer = bundle.get("answer") or {}
    prose = str(answer.get("prose") or "")
    out.append(evaluate_corruption_gate(prose) if prose
               else _not_measurable("corruption::clean",
                                    "recorded bundle carries no answer prose"))
    total = (bundle.get("provenance") or {}).get("latency_seconds_total")
    if total is None:
        total = ((bundle.get("provenance") or {}).get("stages") or {}).get("total_s")
    out.append(evaluate_latency(total, spec["latency_budget_seconds"]))
    return out


def evaluate_question_independent_report(report: dict, spec: dict) -> list[dict]:
    """The slim-report subset that needs no frozen question match."""
    out = list(evaluate_structural_from_report(report))
    prose = str(report.get("answer_prose") or "")
    out.append(evaluate_corruption_gate(prose) if prose
               else _not_measurable("corruption::clean",
                                    "recorded report carries no answer prose"))
    out.append(evaluate_latency(report.get("total_seconds"),
                                spec["latency_budget_seconds"]))
    return out


def question_dependent_gates(mode: str, question: dict | None,
                             questions: dict[str, dict],
                             exclusion_reason: str) -> list[dict]:
    """Question-dependent gates for an unmatched artifact: not_measurable with
    the reason, so the record shows exactly what could not be checked."""
    out: list[dict] = []
    if mode == "full_bundle":
        if question is not None:  # pragma: no cover - caller guarantees None
            for gate in question["truth_gates"]:
                out.append(_not_measurable(f"truth::{gate['id']}", exclusion_reason))
        else:
            out.append(_not_measurable("truth::*", exclusion_reason))
        out += [
            _not_measurable("language::dominant_in_accepted", exclusion_reason),
            _not_measurable("recall::citation_controlling_authority", exclusion_reason),
            _not_measurable("recall::retrieval_controlling_authority", exclusion_reason),
            _not_measurable("structural::geometry_preserved",
                           "needs initial+final pair; single recorded bundle"),
            _not_measurable("structural::progressive_phases",
                           "needs initial+final pair; single recorded bundle"),
        ]
    else:  # slim_report
        if question is not None:  # pragma: no cover - caller guarantees None
            for gate in question["truth_gates"]:
                out.append(_not_measurable(f"truth::{gate['id']}", exclusion_reason))
        else:
            out.append(_not_measurable("truth::*", exclusion_reason))
        out += [
            _not_measurable("language::dominant_in_accepted", exclusion_reason),
            _not_measurable("corruption::clean", exclusion_reason),
            _not_measurable("latency::under_budget", exclusion_reason),
            _not_measurable("recall::citation_controlling_authority", exclusion_reason),
            _not_measurable("recall::retrieval_controlling_authority", exclusion_reason),
        ]
    return out


def evaluate_multilingual_coverage(bundles: list[dict]) -> list[dict]:
    """FR/DE/IT robustness over a recorded same-area multilingual set.

    Each recorded run must (a) have retrieved decisions, (b) cover the query's
    own language, (c) cover at least two Swiss languages (broad retrieval is
    the product's own retrieval-first doctrine).
    """
    out = []
    for b in bundles:
        q = str(b.get("query") or "")
        lang_by_query = {"fr": "fr", "de": "de", "it": "it"}
        # detect query language from the question text itself
        info = classify_language(q)
        qlang = info["dominant"] or "?"
        langs = Counter(str(d.get("language") or "?") for d in b.get("decisions", []))
        n = sum(langs.values())
        qlang_n = langs.get(qlang, 0)
        swiss = set(_MULTILINGUAL["swiss_languages"])
        n_swiss_langs = sum(1 for k in langs if k in swiss)
        label = b.get("_label", q[:40])
        min_swiss = int(_MULTILINGUAL["min_swiss_languages"])
        ok = n > 0 and qlang_n > 0 and n_swiss_langs >= min_swiss
        out.append(_out(
            f"multilingual::{label}",
            ok,
            "" if ok
            else f"query_lang={qlang} n={n} query_lang_n={qlang_n} langs={dict(langs)}",
            query_language=qlang, n_decisions=n, n_swiss_languages=n_swiss_langs,
            languages=dict(langs),
        ))
    return out
