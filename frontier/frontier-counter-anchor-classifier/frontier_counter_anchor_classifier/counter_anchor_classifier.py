"""Sentence-anchored counter-authority label decision component (the candidate).

This is the drop-in decision function the charter BUILDS.  It is not a
measurement and it never issues a served-packet verdict: it decides, for one
candidate decision row, whether the row's own cited passage licenses the
proposed counter label under the accepted frozen support rubric, and otherwise
emits an explicit, COUNTED abstention.

Why it exists
-------------
The accepted measurement LABEL_HALF.json records that the served packet
38839347028 issues 65 counter labels of which only 5 are supported by their own
cited evidence under the frozen rubric (support rate 0.0769).  The defect is
mostly mechanical: 38 rows are OFF-DOMAIN (no pivot anchor to the question
anywhere in the row's own text) and 16 are UNBACKED with the cited-evidence
string empty at counter_uncertainty 0.95-1.0.  An abstain-first decision
function that requires BOTH a domain anchor to the query AND an intent marker
inside a cited passage of that same decision converts those rows into counted
abstentions instead of shipping unsupported labels.

The emission gate
----------------
A non-ABSTAIN label is emitted ONLY when the row's own cited passage carries,
under the frozen normalization and lexicons:

  1. a non-empty cited evidence string (else ABSTAIN / evidence_absent),
  2. no frozen fragment-pointer pattern (else ABSTAIN / pointer_only),
  3. no frozen polarity-inversion construction (else ABSTAIN / polarity_inverted),
  4. no procedural-formula-only construction without an intent marker
     (else ABSTAIN / procedural_formula_no_intent),
  5. at least one frozen counter-intent marker in the cited evidence itself
     (else ABSTAIN / no_intent_marker),
  6. at least one frozen DOMAIN-tier anchor of the row's own question in the
     cited evidence or the row title/regeste (else ABSTAIN / no_domain_anchor),
  7. at least one frozen PIVOT-tier anchor of the row's own question in the
     cited evidence, title or regeste, AND the row language inside the
     question's expected languages, AND a non-foreign legal_area
     (else ABSTAIN / pivot_absent).

Only when every step passes is the row's own proposed counter label emitted.
The gate is exactly the frozen rubric's criteria (i)-(v) read as emission
conditions, so an emitted label is supported by construction and an abstained
row is counted with the reason it failed.  No rubric, lexicon bar or threshold
is edited; the frozen RULES_LABEL.json bytes are the only judgement input.

The decision is a pure function of (row, frozen rules): no network, no model,
no clock, no randomness.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .vendored.normalize import Normalizer
from .vendored.rules import FrozenRules

#: Output label vocabulary (charter acceptance test 2).
LABEL_SUPPORTING = "supporting"
LABEL_CONTRARY = "contrary"
LABEL_LIMITING = "limiting"
LABEL_ABSTAIN = "ABSTAIN"

#: Mapping from the product's issued counter_status to the candidate's label
#: vocabulary.  The candidate CONFIRMS the row's own proposed label; it never
#: invents a polarity the row did not carry.  ``contrary_or_exception`` maps to
#: ``limiting``: an exception narrows the rule even when it is phrased as a
#: contrary position.  The mapping is immaterial to the frozen score (the
#: rubric scores the evidence, not the polarity match) and is documented in the
#: integration contract.
STATUS_TO_LABEL = {
    "candidate-contrary": LABEL_CONTRARY,
    "contrary": LABEL_CONTRARY,
    "contrary_or_exception": LABEL_LIMITING,
    "candidate-limiting": LABEL_LIMITING,
    "limiting": LABEL_LIMITING,
    "supporting": LABEL_SUPPORTING,
}

#: Deterministic per-reason uncertainty for ABSTAIN decisions.  An abstained
#: row is unevidenced BY CONSTRUCTION, so its uncertainty is high; the exact
#: value is a pure function of the reason code (reporting contract, not a
#: tuned threshold).
ABSTAIN_UNCERTAINTY = {
    "evidence_absent": 1.0,
    "pointer_only": 0.9,
    "polarity_inverted": 0.9,
    "procedural_formula_no_intent": 0.85,
    "no_intent_marker": 0.8,
    "no_domain_anchor": 0.8,
    "pivot_absent": 0.8,
}

#: Uncertainty for an emitted label.  Low and fixed: the label is emitted only
#: when the cited passage carries both a domain anchor and an intent marker
#: under the frozen rubric, so the residual uncertainty is the rubric's own
#: residual, not a tuned value.
EMITTED_UNCERTAINTY = 0.2


@dataclass(frozen=True)
class LabelDecision:
    """The candidate's output for one decision row.

    ``label`` is one of {supporting, contrary, limiting, ABSTAIN}.
    ``cited_sentence`` is the row's own cited evidence string (the exact
    passage the decision is anchored to; empty when the row cites nothing).
    ``reason_code`` is ``supported`` for an emitted label and the failing
    frozen-precedence reason for an abstention.
    ``uncertainty`` is the deterministic per-reason value above.
    """

    decision_id: str
    proposed_status: str
    label: str
    cited_sentence: str
    reason_code: str
    uncertainty: float
    language: str = ""
    rank: int | None = None
    criterion_evidence: dict[str, Any] = field(default_factory=dict)

    @property
    def abstained(self) -> bool:
        return self.label == LABEL_ABSTAIN

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "proposed_status": self.proposed_status,
            "label": self.label,
            "cited_sentence": self.cited_sentence,
            "reason_code": self.reason_code,
            "uncertainty": self.uncertainty,
            "language": self.language,
            "rank": self.rank,
            "abstained": self.abstained,
            "criterion_evidence": self.criterion_evidence,
        }


def _lang_of(row: dict[str, Any], fallback: str = "de") -> str:
    lang = str(row.get("language") or "").lower()
    return lang if lang in ("de", "fr", "it") else fallback


def _hits(nz: Normalizer, tokens: list[str], terms: list[str], *, anchor: bool) -> list[str]:
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


def decide_label(
    row: dict[str, Any],
    rules: FrozenRules,
    anchor_profile: dict[str, Any],
) -> LabelDecision:
    """Decide one candidate row: emit its label or COUNT an abstention.

    Pure and deterministic.  ``row`` is a decision row as extracted by the
    vendored extract.counter_rows (it carries counter_status, counter_evidence,
    title, regeste, language, legal_area, rank).  ``rules`` is the frozen
    RULES_LABEL.json.  ``anchor_profile`` is the row's own question profile
    from rules.anchors[qid].

    The emission gate mirrors the frozen rubric's assignment precedence as
    abstention reasons, so the abstained rows carry the same reason codes the
    frozen harness would assign them.
    """
    nz = rules.normalizer
    lex = rules.lexicons
    language = _lang_of(row)
    evidence = str(row.get("counter_evidence") or "")
    title = str(row.get("title") or "")
    regeste = str(row.get("regeste") or "")
    proposed = str(row.get("counter_status") or "")
    did = str(row.get("decision_id") or "")

    ev_rx = nz.regex_text(evidence)
    ev_tokens = nz.stems(evidence)
    # Frozen context window for DOMAIN/PIVOT: cited evidence + title + regeste.
    ctx_tokens = nz.stems(" ".join(x for x in (evidence, title, regeste) if x))
    # Frozen window for DOMAIN (criterion iv): cited evidence + title.
    title_tokens = nz.stems(" ".join(x for x in (evidence, title) if x))

    markers = rules.marker_lexicon(language, "primary")
    markers_hit = _hits(nz, ev_tokens, markers, anchor=False)
    inversion_hit = _rx_hits(nz, ev_rx, lex["polarity_inversion"].get(language) or [])
    procedural_hit = _rx_hits(nz, ev_rx, lex["procedural_formula"].get(language) or [])
    outcome_hit = _hits(
        nz, ev_tokens, lex["procedural_outcome_words"].get(language) or [], anchor=False
    )
    pointer_hit = _rx_hits(nz, nz.regex_text(evidence).strip(), lex["fragment_pointer"])

    domain_anchors = list(anchor_profile.get("domain") or [])
    pivot_anchors = list(anchor_profile.get("pivot") or [])
    expected_languages = list(anchor_profile.get("expected_languages") or [])
    foreign_areas = list(anchor_profile.get("foreign_legal_area_fields") or [])

    domain_ev_title = _hits(nz, title_tokens, domain_anchors, anchor=True)
    pivot_ctx = _hits(nz, ctx_tokens, pivot_anchors, anchor=True)

    evidence_absent = not evidence.strip()
    lang_ok = (not expected_languages) or (language in expected_languages)
    area_ok = str(row.get("legal_area") or "") not in foreign_areas

    # Criterion evidence is recorded on EVERY decision (emitted or abstained)
    # so the integration contract can audit why a label was or was not issued.
    criterion_evidence = {
        "i_intent_marker_in_cited_evidence": {
            "pass": bool(markers_hit), "matches": markers_hit},
        "ii_no_polarity_inversion": {
            "pass": not inversion_hit, "matches": inversion_hit},
        "iii_not_procedural_boilerplate_only": {
            "pass": (not procedural_hit) or bool(outcome_hit) or bool(markers_hit),
            "matches": sorted(set(procedural_hit) | set(outcome_hit))},
        "iv_topical_term_in_evidence_or_title": {
            "pass": bool(domain_ev_title), "matches": domain_ev_title},
        "v_not_demonstrably_outside_question_domain": {
            "pass": bool(pivot_ctx) and lang_ok and area_ok,
            "matches": pivot_ctx,
            "language_ok": lang_ok,
            "legal_area_ok": area_ok},
    }

    base = {
        "decision_id": did,
        "proposed_status": proposed,
        "cited_sentence": evidence,
        "language": language,
        "rank": row.get("rank"),
        "criterion_evidence": criterion_evidence,
    }

    # -- emission gate: the frozen assignment precedence, read as abstention --
    # reasons, in the FROZEN step order, so every abstained row carries the
    # same reason code the frozen harness would assign it.  A row is emitted
    # only when every frozen criterion (i)-(v) passes; the first failing step
    # names the abstention reason.
    if evidence_absent:                                                        # step 1
        return LabelDecision(
            reason_code="evidence_absent",
            uncertainty=ABSTAIN_UNCERTAINTY["evidence_absent"],
            label=LABEL_ABSTAIN, **base)
    if pointer_hit:                                                             # step 2
        return LabelDecision(
            reason_code="pointer_only",
            uncertainty=ABSTAIN_UNCERTAINTY["pointer_only"],
            label=LABEL_ABSTAIN, **base)
    if procedural_hit and not markers_hit:                                      # step 3
        return LabelDecision(
            reason_code="procedural_formula_no_intent",
            uncertainty=ABSTAIN_UNCERTAINTY["procedural_formula_no_intent"],
            label=LABEL_ABSTAIN, **base)
    if inversion_hit:                                                           # step 4
        return LabelDecision(
            reason_code="polarity_inverted",
            uncertainty=ABSTAIN_UNCERTAINTY["polarity_inverted"],
            label=LABEL_ABSTAIN, **base)
    if (not pivot_ctx) or (not lang_ok) or (not area_ok):                       # step 5
        return LabelDecision(
            reason_code="pivot_absent",
            uncertainty=ABSTAIN_UNCERTAINTY["pivot_absent"],
            label=LABEL_ABSTAIN, **base)
    if not markers_hit:                                                         # step 6
        return LabelDecision(
            reason_code="no_intent_marker",
            uncertainty=ABSTAIN_UNCERTAINTY["no_intent_marker"],
            label=LABEL_ABSTAIN, **base)
    if not domain_ev_title:                                                     # step 7
        return LabelDecision(
            reason_code="no_domain_anchor",
            uncertainty=ABSTAIN_UNCERTAINTY["no_domain_anchor"],
            label=LABEL_ABSTAIN, **base)

    # Every frozen criterion passes: emit the row's own proposed label.
    emitted = STATUS_TO_LABEL.get(proposed, LABEL_LIMITING)
    return LabelDecision(
        reason_code="supported",
        uncertainty=EMITTED_UNCERTAINTY,
        label=emitted, **base)


__all__ = [
    "ABSTAIN_UNCERTAINTY",
    "EMITTED_UNCERTAINTY",
    "LABEL_ABSTAIN",
    "LABEL_CONTRARY",
    "LABEL_LIMITING",
    "LABEL_SUPPORTING",
    "LabelDecision",
    "STATUS_TO_LABEL",
    "decide_label",
]
